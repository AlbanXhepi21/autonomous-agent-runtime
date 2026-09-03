"""Tests for explicit artifact registration, metadata, and run isolation."""

import logging
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api.routes.artifacts import download_artifact
from app.api.schemas.agent import AgentRunRequest
from app.artifacts.store import WorkspaceArtifactStore
from app.contracts.actions import AgentAction
from app.environment import Workspace
from app.llm.contracts import LLMClient
from app.tools.artifacts import RegisterArtifactTool
from app.tools.execution import ToolExecutor
from app.tools.filesystem import WriteFileTool
from app.tools.registry import ToolRegistry
from tests.support import make_runner, make_tenant_context, run_agent_directly

WORKSPACE_ID = uuid.uuid4()


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
        run_id="run-one", workspace_id=str(WORKSPACE_ID), iteration=1,
    )

    artifact = result.output["artifact"]
    assert result.success and artifact["run_id"] == "run-one"
    assert artifact["relative_path"].startswith("artifacts/run-one/")
    assert artifact["size"] == len("# Report\n")
    path = await store.path_for(workspace_id=WORKSPACE_ID, artifact_id=artifact["id"])
    assert path.read_text() == "# Report\n"


@pytest.mark.asyncio
async def test_artifact_rejects_external_or_traversal_source_paths(tmp_path: Path) -> None:
    tools, _ = artifact_tools(tmp_path)
    outside = await ToolExecutor(tools).execute(
        "register_artifact", {"source_path": "../secret.txt"}, run_id="run", workspace_id=str(WORKSPACE_ID), iteration=1,
    )
    absolute = await ToolExecutor(tools).execute(
        "register_artifact", {"source_path": "/tmp/secret.txt"}, run_id="run", workspace_id=str(WORKSPACE_ID), iteration=1,
    )

    assert not outside.success and not absolute.success


@pytest.mark.asyncio
async def test_artifact_store_enforces_size_and_run_directory_containment(tmp_path: Path) -> None:
    (tmp_path / "large.txt").write_text("x" * 11)
    (tmp_path / "small.txt").write_text("small")
    store = WorkspaceArtifactStore(Workspace(tmp_path), max_artifact_bytes=10)

    with pytest.raises(ValueError, match="size limit"):
        await store.register(workspace_id=WORKSPACE_ID, run_id="run", source_path="large.txt")
    with pytest.raises(ValueError):
        await store.register(workspace_id=WORKSPACE_ID, run_id="../escape", source_path="small.txt")


@pytest.mark.asyncio
async def test_multiple_artifacts_and_runs_remain_isolated(tmp_path: Path) -> None:
    (tmp_path / "one.txt").write_text("one")
    (tmp_path / "two.txt").write_text("two")
    tools, store = artifact_tools(tmp_path)
    executor = ToolExecutor(tools)
    first = await executor.execute(
        "register_artifact", {"source_path": "one.txt"}, run_id="first", workspace_id=str(WORKSPACE_ID), iteration=1,
    )
    second = await executor.execute(
        "register_artifact", {"source_path": "two.txt"}, run_id="second", workspace_id=str(WORKSPACE_ID), iteration=1,
    )

    assert first.output["artifact"]["id"] != second.output["artifact"]["id"]
    first_path = await store.path_for(workspace_id=WORKSPACE_ID, artifact_id=first.output["artifact"]["id"])
    second_path = await store.path_for(workspace_id=WORKSPACE_ID, artifact_id=second.output["artifact"]["id"])
    assert first_path.parent.parent.name == "first"
    assert second_path.parent.parent.name == "second"
    assert await store.path_for(workspace_id=WORKSPACE_ID, artifact_id="../first") is None


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
    response = await run_agent_directly(
        AgentRunRequest(goal="Create a report"), runner, context=make_tenant_context(workspace_id=WORKSPACE_ID),
    )

    assert response.final_answer == "Report created."
    assert len(response.artifacts) == 1
    assert response.artifacts[0].run_id == response.run_id
    assert not hasattr(response.artifacts[0], "content")


class _StubTenancyService:
    """``download_artifact`` resolves the artifact's owning workspace itself and
    verifies membership through a real ``TenancyService`` call -- this stands in
    for one, always confirming the caller belongs to whatever workspace it asks
    about, since this test isn't exercising the membership-denied path (that is
    covered in ``tests/api/test_tenant_isolation.py``).
    """

    def __init__(self, context) -> None:
        self._context = context

    async def get_context(self, *, user, workspace_id):
        return self._context


@pytest.mark.asyncio
async def test_artifact_download_uses_validated_ids_only(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    (tmp_path / "download.txt").write_text("download")
    _, store = artifact_tools(tmp_path)
    artifact = await store.register(workspace_id=WORKSPACE_ID, run_id="run", source_path="download.txt")
    caplog.set_level(logging.INFO)
    context = make_tenant_context(workspace_id=WORKSPACE_ID)
    tenancy = _StubTenancyService(context)

    response = await download_artifact(artifact.id, context.user, store, tenancy)
    with pytest.raises(HTTPException) as missing:
        await download_artifact("../download.txt", context.user, store, tenancy)

    assert response.path == await store.path_for(workspace_id=WORKSPACE_ID, artifact_id=artifact.id)
    assert missing.value.status_code == 404
    assert any(record.getMessage() == "artifact_accessed" for record in caplog.records)
