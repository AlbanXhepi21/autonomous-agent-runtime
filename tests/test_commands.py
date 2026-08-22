"""Tests for argv-only, workspace-scoped command execution."""

import logging
from pathlib import Path

import pytest

from app.contracts.actions import AgentAction
from app.agent.registry import AgentRegistry
from app.core.limits import RuntimeLimits
from app.environment import CommandExecutor, PythonExecutor, Workspace
from app.environment.repository import Repository
from app.artifacts.store import WorkspaceArtifactStore
from app.llm.base import LLMClient
from app.skills.registry import SkillRegistry
from app.tools.calculator import CalculatorTool
from app.tools.commands import RunCommandTool
from app.tools.execution import ToolExecutor
from app.tools.filesystem import ListFilesTool, ReadFileTool, WriteFileTool
from app.tools.python_exec import PythonExecTool
from app.tools.repository import GetChangedFilesTool, GetRepositoryTreeTool, GitInspectTool, SearchFilesTool
from app.tools.artifacts import RegisterArtifactTool
from app.tools.registry import ToolRegistry
from tests.support import make_runner


def command_registry(root: Path, *, timeout: float = 2, output: int = 1_024) -> ToolRegistry:
    workspace = Workspace(root)
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(ListFilesTool(workspace))
    registry.register(ReadFileTool(workspace))
    registry.register(WriteFileTool(workspace))
    registry.register(RunCommandTool(CommandExecutor(
        workspace, allowed_commands=("pytest",), timeout_seconds=timeout, max_output_bytes=output,
    )))
    registry.register(PythonExecTool(PythonExecutor(workspace)))
    repository = Repository(workspace)
    registry.register(GetRepositoryTreeTool(repository))
    registry.register(SearchFilesTool(repository))
    registry.register(GetChangedFilesTool(repository))
    registry.register(GitInspectTool(repository))
    registry.register(RegisterArtifactTool(WorkspaceArtifactStore(workspace)))
    return registry


async def run_pytest(executor: ToolExecutor, *args: str, **extra: object) -> dict[str, object]:
    result = await executor.execute("run_command", {"command": "pytest", "args": list(args), **extra})
    assert result.success
    assert isinstance(result.output, dict)
    return result.output


@pytest.mark.asyncio
async def test_allowed_command_captures_stdout_and_stderr(tmp_path: Path) -> None:
    (tmp_path / "test_output.py").write_text(
        "import sys\n\ndef test_output():\n print('standard output'); sys.stderr.write('standard error\\n')\n"
    )
    output = await run_pytest(ToolExecutor(command_registry(tmp_path)), "-s", "-q", "test_output.py")

    assert output["success"] is True
    assert "standard output" in str(output["stdout"])
    assert "standard error" in str(output["stderr"])
    assert output["return_code"] == 0


@pytest.mark.asyncio
async def test_unknown_or_outside_allowlist_command_is_denied(tmp_path: Path) -> None:
    executor = ToolExecutor(command_registry(tmp_path))
    unknown = await executor.execute("run_command", {"command": "not-a-command"})
    disallowed = await executor.execute("run_command", {"command": "echo", "args": ["hello"]})

    assert unknown.success and unknown.output["success"] is False
    assert disallowed.success and disallowed.output["success"] is False
    assert "not allowed" in str(disallowed.output["error"])


@pytest.mark.asyncio
async def test_shell_syntax_is_rejected_and_never_executes(tmp_path: Path) -> None:
    executor = ToolExecutor(command_registry(tmp_path))
    output = await run_pytest(executor, "-q; touch injected.txt")

    assert output["success"] is False
    assert "shell control syntax" in str(output["error"])
    assert not (tmp_path / "injected.txt").exists()


@pytest.mark.asyncio
async def test_working_directory_is_workspace_scoped(tmp_path: Path) -> None:
    child = tmp_path / "child"
    child.mkdir()
    (child / "test_ok.py").write_text("def test_ok(): assert True\n")
    executor = ToolExecutor(command_registry(tmp_path))
    inside = await run_pytest(executor, "-q", "test_ok.py", working_directory="child")
    traversal = await run_pytest(executor, "-q", working_directory="../")

    assert inside["success"] is True
    assert traversal["success"] is False
    assert "outside" in str(traversal["error"])


@pytest.mark.asyncio
async def test_timeout_and_output_truncation_are_structured(tmp_path: Path) -> None:
    (tmp_path / "test_slow.py").write_text("import time\ndef test_slow(): time.sleep(1)\n")
    timed_out = await run_pytest(ToolExecutor(command_registry(tmp_path, timeout=0.05)), "-q", "test_slow.py")
    assert timed_out["success"] is False and timed_out["timed_out"] is True

    (tmp_path / "test_long.py").write_text("def test_long(): print('x' * 500)\n")
    truncated = await run_pytest(
        ToolExecutor(command_registry(tmp_path, output=80)), "-s", "-q", "test_long.py"
    )
    assert truncated["stdout_truncated"] is True
    assert len(str(truncated["stdout"]).encode()) <= 80


@pytest.mark.asyncio
async def test_minimal_environment_and_nonzero_exit_are_returned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-reach-command")
    (tmp_path / "test_env.py").write_text(
        "import os\ndef test_env(): print(os.getenv('OPENAI_API_KEY', 'missing')); assert False\n"
    )
    output = await run_pytest(ToolExecutor(command_registry(tmp_path)), "-s", "-q", "test_env.py")

    assert output["success"] is False
    assert output["return_code"] != 0
    assert "missing" in str(output["stdout"])
    assert "must-not-reach-command" not in str(output)


@pytest.mark.asyncio
async def test_command_events_and_specialist_capability_restriction(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    tools = command_registry(tmp_path)
    result = await ToolExecutor(tools).execute("run_command", {"command": "echo"}, run_id="run", iteration=2)
    registry = AgentRegistry(tool_registry=tools, skill_registry=SkillRegistry())

    assert result.output["success"] is False
    event = next(record.event_fields for record in caplog.records if record.getMessage() == "command_execution_denied")
    assert event["run_id"] == "run" and event["command"] == "echo"
    assert "run_command" in registry.get_metadata("software_engineer").allowed_tools
    assert "run_command" not in registry.get_metadata("research").allowed_tools
    assert "run_command" not in registry.get_metadata("data_analyst").allowed_tools


class CommandFailureThenFinishLLM(LLMClient):
    def __init__(self) -> None:
        self.calls = 0

    async def choose_action(self, *, system_prompt: str, context: dict[str, object]) -> AgentAction:
        self.calls += 1
        if self.calls == 1:
            return AgentAction(
                action_type="use_tool", reasoning_summary="Check the command result.",
                tool_name="run_command", tool_arguments={"command": "echo"},
            )
        return AgentAction(
            action_type="finish", reasoning_summary="Recoverable failure handled.", final_answer="Done."
        )


@pytest.mark.asyncio
async def test_parent_run_continues_after_a_recoverable_command_failure(tmp_path: Path) -> None:
    tools = command_registry(tmp_path)
    llm = CommandFailureThenFinishLLM()
    outcome = await make_runner(
        llm, tools, limits=RuntimeLimits(max_iterations=3),
    ).run("Verify command handling")

    assert outcome.final_answer == "Done."
    assert llm.calls == 2
