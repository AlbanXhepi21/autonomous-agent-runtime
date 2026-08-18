"""Tests for bounded repository inspection and controlled change tracking."""

import asyncio
import logging
import shutil
from pathlib import Path

import pytest

from app.agent.registry import AgentRegistry
from app.environment import CommandExecutor, PythonExecutor, Workspace
from app.environment.repository import Repository
from app.artifacts.store import WorkspaceArtifactStore
from app.skills.registry import SkillRegistry
from app.tools.calculator import CalculatorTool
from app.tools.commands import RunCommandTool
from app.tools.executor import ToolExecutor
from app.tools.filesystem import ListFilesTool, ReadFileTool, WriteFileTool
from app.tools.python_exec import PythonExecTool
from app.tools.registry import ToolRegistry
from app.tools.repository import GetChangedFilesTool, GetRepositoryTreeTool, GitInspectTool, SearchFilesTool
from app.tools.artifacts import RegisterArtifactTool


def repository_registry(root: Path, *, entries: int = 20, search_results: int = 10) -> ToolRegistry:
    workspace = Workspace(root)
    repository = Repository(workspace, max_entries=entries, max_search_results=search_results)
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(ListFilesTool(workspace))
    registry.register(ReadFileTool(workspace))
    registry.register(WriteFileTool(workspace))
    registry.register(RunCommandTool(CommandExecutor(workspace)))
    registry.register(PythonExecTool(PythonExecutor(workspace)))
    registry.register(GetRepositoryTreeTool(repository))
    registry.register(SearchFilesTool(repository))
    registry.register(GetChangedFilesTool(repository))
    registry.register(GitInspectTool(repository))
    registry.register(RegisterArtifactTool(WorkspaceArtifactStore(workspace)))
    return registry


@pytest.mark.asyncio
async def test_repository_tree_and_search_ignore_generated_directories(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("MARKER = 'visible'\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "generated.js").write_text("visible")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("hidden")
    executor = ToolExecutor(repository_registry(tmp_path, entries=3, search_results=1))

    tree = await executor.execute("get_repository_tree", {"max_depth": 3})
    path_search = await executor.execute("search_files", {"path_query": "app"})
    text_search = await executor.execute("search_files", {"text_query": "visible", "max_results": 1})

    assert tree.success and len(tree.output) <= 3
    assert "src/app.py" in {item["path"] for item in tree.output}
    assert all("node_modules" not in item["path"] and ".git" not in item["path"] for item in tree.output)
    assert path_search.output == [{"path": "src/app.py", "text_matches": 0}]
    assert text_search.output == [{"path": "src/app.py", "text_matches": 1}]


@pytest.mark.asyncio
async def test_workspace_edit_is_tracked_and_outside_edit_is_rejected(tmp_path: Path) -> None:
    executor = ToolExecutor(repository_registry(tmp_path))
    written = await executor.execute("write_file", {"path": "src/new.py", "content": "value = 1", "create_parents": True}, run_id="run", iteration=1)
    changed = await executor.execute("get_changed_files", {})
    outside = await executor.execute("write_file", {"path": "../outside.py", "content": "no"})

    assert written.success and changed.output == ["src/new.py"]
    assert not outside.success and not (tmp_path.parent / "outside.py").exists()


@pytest.mark.asyncio
async def test_git_inspection_is_fixed_read_only_and_logs_repository_events(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    git = shutil.which("git")
    if git is None:
        pytest.skip("Git is unavailable.")
    init = await asyncio.create_subprocess_exec(git, "init", cwd=str(tmp_path))
    assert await init.wait() == 0
    caplog.set_level(logging.INFO)
    executor = ToolExecutor(repository_registry(tmp_path))
    status = await executor.execute("git_inspect", {"operation": "status"})
    destructive = await executor.execute("git_inspect", {"operation": "reset --hard"})

    assert status.success and status.output["success"] is True
    assert destructive.success is False and "not allowed" in (destructive.error or "")
    events = [record.getMessage() for record in caplog.records]
    assert "repository_inspection" in events


def test_repository_capabilities_are_scoped_to_software_engineer(tmp_path: Path) -> None:
    registry = AgentRegistry(tool_registry=repository_registry(tmp_path), skill_registry=SkillRegistry())

    engineer = registry.get_metadata("software_engineer")
    assert {"write_file", "search_files", "get_repository_tree", "git_inspect"}.issubset(engineer.allowed_tools)
    assert "write_file" not in registry.get_metadata("research").allowed_tools
    assert "search_files" not in registry.get_metadata("data_analyst").allowed_tools
