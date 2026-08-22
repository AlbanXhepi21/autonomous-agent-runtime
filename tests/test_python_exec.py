"""Tests for restricted local Python child-process execution."""

import asyncio
import logging
from pathlib import Path

import pytest

from app.agent.registry import AgentRegistry
from app.environment import CommandExecutor, PythonExecutor, Workspace
from app.environment.repository import Repository
from app.artifacts.store import WorkspaceArtifactStore
from app.skills.registry import SkillRegistry
from app.tools.calculator import CalculatorTool
from app.tools.commands import RunCommandTool
from app.tools.execution import ToolExecutor
from app.tools.filesystem import ListFilesTool, ReadFileTool, WriteFileTool
from app.tools.python_exec import PythonExecTool
from app.tools.repository import GetChangedFilesTool, GetRepositoryTreeTool, GitInspectTool, SearchFilesTool
from app.tools.artifacts import RegisterArtifactTool
from app.tools.registry import ToolRegistry


def python_registry(root: Path, *, timeout: float = 1, code_limit: int = 1_024, output: int = 1_024) -> ToolRegistry:
    workspace = Workspace(root)
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(ListFilesTool(workspace))
    registry.register(ReadFileTool(workspace))
    registry.register(WriteFileTool(workspace))
    registry.register(RunCommandTool(CommandExecutor(workspace)))
    registry.register(PythonExecTool(PythonExecutor(
        workspace, timeout_seconds=timeout, max_code_bytes=code_limit, max_output_bytes=output,
    )))
    repository = Repository(workspace)
    registry.register(GetRepositoryTreeTool(repository))
    registry.register(SearchFilesTool(repository))
    registry.register(GetChangedFilesTool(repository))
    registry.register(GitInspectTool(repository))
    registry.register(RegisterArtifactTool(WorkspaceArtifactStore(workspace)))
    return registry


async def run_code(executor: ToolExecutor, code: str, **kwargs: object) -> dict[str, object]:
    result = await executor.execute("python_exec", {"code": code}, **kwargs)
    assert result.success
    assert isinstance(result.output, dict)
    return result.output


@pytest.mark.asyncio
async def test_python_exec_runs_arithmetic_in_a_separate_child_process(tmp_path: Path) -> None:
    output = await run_code(
        ToolExecutor(python_registry(tmp_path)), "import math\nprint(math.sqrt(81))"
    )

    assert output["success"] is True
    assert output["stdout"] == "9.0\n"
    assert output["return_code"] == 0


@pytest.mark.asyncio
async def test_python_exec_reports_syntax_and_runtime_failures(tmp_path: Path) -> None:
    executor = ToolExecutor(python_registry(tmp_path))
    syntax = await run_code(executor, "if True print('bad')")
    runtime = await run_code(executor, "raise ValueError('expected failure')")

    assert syntax["success"] is False
    assert syntax["error"] == "Python source is invalid."
    assert runtime["success"] is False
    assert "ValueError" in str(runtime["stderr"])
    assert runtime["return_code"] == 1


@pytest.mark.asyncio
async def test_python_exec_enforces_timeout_source_and_output_limits(tmp_path: Path) -> None:
    timeout = await run_code(ToolExecutor(python_registry(tmp_path, timeout=0.05)), "while True: pass")
    oversized = await run_code(ToolExecutor(python_registry(tmp_path, code_limit=8)), "print('too long')")
    truncated = await run_code(
        ToolExecutor(python_registry(tmp_path, output=80)), "print('x' * 500)"
    )

    assert timeout["success"] is False and timeout["timed_out"] is True
    assert oversized["success"] is False and "size limit" in str(oversized["error"])
    assert truncated["success"] is True and truncated["stdout_truncated"] is True
    assert len(str(truncated["stdout"]).encode()) <= 80


@pytest.mark.asyncio
async def test_python_exec_rejects_prohibited_imports_and_keeps_secrets_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-reach-python")
    executor = ToolExecutor(python_registry(tmp_path))
    prohibited = await run_code(executor, "import os\nprint(os.getenv('OPENAI_API_KEY'))")
    allowed = await run_code(executor, "import json\nprint(json.dumps({'key': 'value'}))")

    assert prohibited["success"] is False
    assert "not allowed" in str(prohibited["error"])
    assert allowed["success"] is True
    assert "must-not-reach-python" not in str(allowed)


@pytest.mark.asyncio
async def test_python_exec_cleans_temporary_files_and_concurrent_runs_are_isolated(tmp_path: Path) -> None:
    executor = ToolExecutor(python_registry(tmp_path))
    first, second = await asyncio.gather(
        run_code(executor, "print('first')"),
        run_code(executor, "print('second')"),
    )

    assert first["stdout"] == "first\n"
    assert second["stdout"] == "second\n"
    assert not list(tmp_path.glob("python-exec-*"))


@pytest.mark.asyncio
async def test_python_execution_logging_and_specialist_capabilities(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    tools = python_registry(tmp_path)
    result = await ToolExecutor(tools).execute("python_exec", {"code": "print(1)"}, run_id="run", iteration=2)
    registry = AgentRegistry(tool_registry=tools, skill_registry=SkillRegistry())

    event = next(record.event_fields for record in caplog.records if record.getMessage() == "python_execution_finished")
    assert result.output["success"] is True
    assert event["run_id"] == "run" and event["code_bytes"] == len("print(1)".encode())
    assert "python_exec" not in registry.get_metadata("data_analyst").allowed_tools
    assert "python_exec" in registry.get_metadata("software_engineer").allowed_tools
    assert "python_exec" not in registry.get_metadata("research").allowed_tools
