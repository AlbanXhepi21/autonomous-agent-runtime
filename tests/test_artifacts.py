"""Tests for explicit artifact registration, metadata, and run isolation."""

from pathlib import Path
import logging

import pytest

from app.contracts.actions import AgentAction
from app.api.routes.agent import run_agent
from app.api.routes.artifacts import download_artifact
from app.api.schemas.agent import AgentRunRequest
from app.artifacts.store import WorkspaceArtifactStore
from app.environment import Workspace
from app.llm.base import LLMClient
from app.tools.artifacts import RegisterArtifactTool
from app.tools.execution import ToolExecutor
from app.tools.filesystem import WriteFileTool
from app.tools.registry import ToolRegistry
from fastapi import HTTPException
from tests.support import make_runner


def artifact_tools(root: Path) -> tuple[ToolRegistry, WorkspaceArtifactStore]:
    workspace = Workspace(root)
    store = WorkspaceArtifactStore(workspace)
    tools = ToolRegistry()
    tools.register(WriteFileTool(workspace))
    tools.register(RegisterArtifactTool(store))
    return tools, store


@pytest.mark.asyncio
async def test_register_artifact_copies_workspace_file_with_metadata(tmp_path: Path) -> None:
    (tmp_path / "report.md").write_text("# Report\n")
    tools, store = artifact_tools(tmp_path)
    result = await ToolExecutor(tools).execute(
        "register_artifact",
        {"source_path": "report.md", "artifact_type": "report", "media_type": "text/markdown", "metadata": {"topic": "test"}},
        run_id="run-one", iteration=1,
    )

    artifact = result.output["artifact"]
    assert result.success and artifact["run_id"] == "run-one"
    assert artifact["relative_path"].startswith("artifacts/run-one/")
    assert artifact["size"] == len("# Report\n")
    assert store.path_for(artifact["id"]).read_text() == "# Report\n"


@pytest.mark.asyncio
async def test_artifact_rejects_external_or_traversal_source_paths(tmp_path: Path) -> None:
    tools, _ = artifact_tools(tmp_path)
    outside = await ToolExecutor(tools).execute("register_artifact", {"source_path": "../secret.txt"}, run_id="run", iteration=1)
    absolute = await ToolExecutor(tools).execute("register_artifact", {"source_path": "/tmp/secret.txt"}, run_id="run", iteration=1)

    assert not outside.success and not absolute.success


def test_artifact_store_enforces_size_and_run_directory_containment(tmp_path: Path) -> None:
    (tmp_path / "large.txt").write_text("x" * 11)
    (tmp_path / "small.txt").write_text("small")
    store = WorkspaceArtifactStore(Workspace(tmp_path), max_artifact_bytes=10)

    with pytest.raises(ValueError, match="size limit"):
        store.register(run_id="run", source_path="large.txt")
    with pytest.raises(ValueError):
        store.register(run_id="../escape", source_path="small.txt")


@pytest.mark.asyncio
async def test_multiple_artifacts_and_runs_remain_isolated(tmp_path: Path) -> None:
    (tmp_path / "one.txt").write_text("one")
    (tmp_path / "two.txt").write_text("two")
    tools, store = artifact_tools(tmp_path)
    executor = ToolExecutor(tools)
    first = await executor.execute("register_artifact", {"source_path": "one.txt"}, run_id="first", iteration=1)
    second = await executor.execute("register_artifact", {"source_path": "two.txt"}, run_id="second", iteration=1)

    assert first.output["artifact"]["id"] != second.output["artifact"]["id"]
    assert store.path_for(first.output["artifact"]["id"]).parent.name == "first"
    assert store.path_for(second.output["artifact"]["id"]).parent.name == "second"
    assert store.path_for("../first") is None


class ArtifactLLM(LLMClient):
    def __init__(self) -> None: self.calls = 0
    async def choose_action(self, *, system_prompt: str, context: dict[str, object]) -> AgentAction:
        self.calls += 1
        if self.calls == 1:
            return AgentAction(action_type="use_tool", reasoning_summary="Write a report.", tool_name="write_file", tool_arguments={"path": "report.txt", "content": "done"})
        if self.calls == 2:
            return AgentAction(action_type="use_tool", reasoning_summary="Expose report.", tool_name="register_artifact", tool_arguments={"source_path": "report.txt", "artifact_type": "report"})
        return AgentAction(action_type="finish", reasoning_summary="Finished.", final_answer="Report created.")


@pytest.mark.asyncio
async def test_final_agent_response_includes_metadata_not_artifact_content(tmp_path: Path) -> None:
    tools, _ = artifact_tools(tmp_path)
    runner = make_runner(ArtifactLLM(), tools)
    response = await run_agent(AgentRunRequest(goal="Create a report"), runner)

    assert response.final_answer == "Report created."
    assert len(response.artifacts) == 1
    assert response.artifacts[0].run_id == response.run_id
    assert not hasattr(response.artifacts[0], "content")


@pytest.mark.asyncio
async def test_artifact_download_uses_validated_ids_only(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    (tmp_path / "download.txt").write_text("download")
    _, store = artifact_tools(tmp_path)
    artifact = store.register(run_id="run", source_path="download.txt")
    caplog.set_level(logging.INFO)

    response = await download_artifact(artifact.id, store)
    with pytest.raises(HTTPException) as missing:
        await download_artifact("../download.txt", store)

    assert response.path == store.path_for(artifact.id)
    assert missing.value.status_code == 404
    assert any(record.getMessage() == "artifact_accessed" for record in caplog.records)
