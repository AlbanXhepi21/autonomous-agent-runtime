"""Tests for workspace-scoped filesystem tools and path isolation."""

import logging
from pathlib import Path

import pytest

from app.agent.registry import AgentRegistry
from app.agent.delegation import DelegationContext, DelegationRequest, SequentialSubagentExecutor
from app.agent.models import AgentAction
from app.environment import CommandExecutor, PythonExecutor, Workspace, WorkspaceLimits
from app.environment.repository import Repository
from app.artifacts.store import WorkspaceArtifactStore
from app.tools.calculator import CalculatorTool
from app.tools.commands import RunCommandTool
from app.tools.executor import ToolExecutor
from app.tools.filesystem import ListFilesTool, ReadFileTool, WriteFileTool
from app.tools.python_exec import PythonExecTool
from app.tools.repository import GetChangedFilesTool, GetRepositoryTreeTool, GitInspectTool, SearchFilesTool
from app.tools.artifacts import RegisterArtifactTool
from app.tools.registry import ToolRegistry
from app.llm.base import LLMClient
from app.skills.registry import SkillRegistry
from app.core.limits import RuntimeLimits


def filesystem_registry(root: Path, limits: WorkspaceLimits | None = None) -> ToolRegistry:
    workspace = Workspace(root, limits)
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(ListFilesTool(workspace))
    registry.register(ReadFileTool(workspace))
    registry.register(WriteFileTool(workspace))
    registry.register(RunCommandTool(CommandExecutor(workspace)))
    registry.register(PythonExecTool(PythonExecutor(workspace)))
    repository = Repository(workspace)
    registry.register(GetRepositoryTreeTool(repository))
    registry.register(SearchFilesTool(repository))
    registry.register(GetChangedFilesTool(repository))
    registry.register(GitInspectTool(repository))
    registry.register(RegisterArtifactTool(WorkspaceArtifactStore(workspace)))
    return registry


class FinishLLM(LLMClient):
    def __init__(self) -> None:
        self.contexts: list[dict[str, object]] = []

    async def choose_action(self, *, system_prompt: str, context: dict[str, object]) -> AgentAction:
        self.contexts.append(context)
        return AgentAction(action_type="finish", reasoning_summary="Done.", final_answer="Done.")


@pytest.mark.asyncio
async def test_list_read_write_and_nested_workspace_paths(tmp_path: Path) -> None:
    executor = ToolExecutor(filesystem_registry(tmp_path))

    written = await executor.execute(
        "write_file", {"path": "notes/answer.txt", "content": "hello", "create_parents": True}
    )
    listed = await executor.execute("list_files", {"path": "notes"})
    read = await executor.execute("read_file", {"path": "notes/answer.txt"})

    assert written.success and written.output == {"path": "notes/answer.txt", "status": "written"}
    assert listed.success and listed.output == ["notes/answer.txt"]
    assert read.success and read.output == "hello"
    assert (tmp_path / "notes" / "answer.txt").read_text() == "hello"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["../outside.txt", "../../etc/passwd", "/tmp/outside.txt"])
async def test_workspace_rejects_traversal_and_external_absolute_paths(tmp_path: Path, path: str) -> None:
    executor = ToolExecutor(filesystem_registry(tmp_path))

    result = await executor.execute("read_file", {"path": path})

    assert not result.success
    assert result.error in {"Path is outside the workspace.", "Workspace paths must be relative."}


@pytest.mark.asyncio
async def test_workspace_enforces_read_write_and_list_bounds(tmp_path: Path) -> None:
    (tmp_path / "large.txt").write_text("x" * 11)
    for name in ("a.txt", "b.txt", "c.txt"):
        (tmp_path / name).write_text(name)
    executor = ToolExecutor(
        filesystem_registry(tmp_path, WorkspaceLimits(max_file_read_bytes=10, max_file_write_bytes=10, max_list_files=2))
    )

    oversized_read = await executor.execute("read_file", {"path": "large.txt"})
    oversized_write = await executor.execute("write_file", {"path": "new.txt", "content": "x" * 11})
    listed = await executor.execute("list_files", {})

    assert not oversized_read.success and "read size limit" in (oversized_read.error or "")
    assert not oversized_write.success and "write size limit" in (oversized_write.error or "")
    assert listed.success and len(listed.output) == 2
    assert not (tmp_path / "new.txt").exists()


@pytest.mark.asyncio
async def test_workspace_rejects_binary_invalid_text_and_missing_files(tmp_path: Path) -> None:
    (tmp_path / "binary.bin").write_bytes(b"text\0binary")
    (tmp_path / "invalid.txt").write_bytes(b"\xff\xfe")
    executor = ToolExecutor(filesystem_registry(tmp_path))

    binary = await executor.execute("read_file", {"path": "binary.bin"})
    invalid = await executor.execute("read_file", {"path": "invalid.txt"})
    missing = await executor.execute("read_file", {"path": "missing.txt"})

    assert binary.error == "Workspace file appears to be binary."
    assert invalid.error == "Workspace file is not valid UTF-8 text."
    assert missing.error == "Workspace file does not exist."


@pytest.mark.asyncio
async def test_workspace_rejects_outside_symlink_targets(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("private")
    link = tmp_path / "outside-link.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlinks are unavailable on this platform.")
    executor = ToolExecutor(filesystem_registry(tmp_path))

    result = await executor.execute("read_file", {"path": "outside-link.txt"})

    assert not result.success
    assert result.error == "Path is outside the workspace."


@pytest.mark.asyncio
async def test_filesystem_operations_are_logged_without_file_content(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    executor = ToolExecutor(filesystem_registry(tmp_path))

    result = await executor.execute(
        "write_file", {"path": "safe.txt", "content": "DO-NOT-LOG-CONTENT"}, run_id="run-1", iteration=2
    )

    event = next(record.event_fields for record in caplog.records if record.getMessage() == "filesystem_operation_finished")
    assert result.success
    assert event["run_id"] == "run-1"
    assert event["tool"] == "write_file"
    assert event["relative_path"] == "safe.txt"
    assert "DO-NOT-LOG-CONTENT" not in str(event)
    argument_event = next(record.event_fields for record in caplog.records if record.getMessage() == "tool_execution_arguments")
    assert "DO-NOT-LOG-CONTENT" not in str(argument_event)


def test_software_engineer_has_scoped_repository_edit_capabilities(tmp_path: Path) -> None:
    tools = filesystem_registry(tmp_path)
    registry = AgentRegistry(tool_registry=tools)

    engineer = registry.get_metadata("software_engineer")
    assert {"list_files", "read_file"}.issubset(engineer.allowed_tools)
    assert "run_command" in engineer.allowed_tools
    assert "write_file" in engineer.allowed_tools
    assert "read_file" not in registry.get_metadata("research").allowed_tools
    assert "read_file" not in registry.get_metadata("data_analyst").allowed_tools


@pytest.mark.asyncio
async def test_software_engineer_child_receives_only_granted_filesystem_tools(tmp_path: Path) -> None:
    tools = filesystem_registry(tmp_path)
    registry = AgentRegistry(tool_registry=tools, skill_registry=SkillRegistry())
    llm = FinishLLM()
    executor = SequentialSubagentExecutor(
        agent_registry=registry,
        tool_registry=tools,
        skill_registry=SkillRegistry(),
        llm_client_factory=lambda _definition: llm,
        parent_limits=RuntimeLimits(),
    )

    result = await executor.execute(
        DelegationRequest(
            parent_run_id="parent", parent_iteration=1, target_agent="software_engineer",
            objective="Inspect workspace files.",
            context=DelegationContext(objective="Inspect workspace files."),
        )
    )

    assert result.success
    tool_names = [tool["name"] for tool in llm.contexts[0]["available_tools"]]
    assert set(tool_names) == {
        "calculator", "list_files", "read_file", "write_file", "run_command", "python_exec",
        "get_repository_tree", "search_files", "get_changed_files", "git_inspect", "register_artifact",
    }


@pytest.mark.asyncio
async def test_separate_workspace_roots_are_isolated(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    first_executor = ToolExecutor(filesystem_registry(first))
    second_executor = ToolExecutor(filesystem_registry(second))
    await first_executor.execute("write_file", {"path": "only-first.txt", "content": "first"})

    result = await second_executor.execute("read_file", {"path": "../first/only-first.txt"})

    assert not result.success
    assert result.error == "Path is outside the workspace."
