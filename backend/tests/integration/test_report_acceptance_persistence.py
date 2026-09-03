"""The acceptance scenario's artifacts, retrieved after the store that made them is gone.

Publishing and downloading in one process proves nothing about durability: the
in-process registry would pass that test and still lose every link at restart.
Here the publishing store and its connection pool are disposed before anything
is read back, and retrieval goes through a store built afterwards over a new
pool — so the only thing that can still find these files is the database.

Skips when TEST_DATABASE_URL is unset, like the other database tests.
"""

from __future__ import annotations

import os
import zipfile
from hashlib import sha256
from pathlib import Path
from uuid import UUID

import pytest
from docx import Document
from pypdf import PdfReader
from pytest_asyncio import fixture
from sqlalchemy import delete

pytest.importorskip("sqlalchemy")

from app.analytics.presentation.templates import ReportTemplateRegistry
from app.api.routes.artifacts import download_artifact, list_artifacts
from app.artifacts.contracts import ArtifactStatus
from app.artifacts.files import WorkspaceArtifactFiles, digest_of
from app.artifacts.postgres import PostgresArtifactStore
from app.db.records import ArtifactRecord
from app.db.session import Database
from app.environment.workspace import Workspace
from app.orchestration.publishing import ReportPublisher
from tests.fixtures.payment_failures import PERIOD, RUN_ID, conversation_store
from tests.support import make_artifact_route_caller

pytestmark = pytest.mark.postgres

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
TEMPLATE = "monthly_business_review"
#: The legacy workspace seeded by migration 20260903_0016 -- always present,
#: so single-tenant tests can use it as a valid FK target without minting rows.
WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000001")


class Deployment:
    """Stands in for the running application: build one, then throw it away."""

    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root
        self._databases: list[Database] = []

    def store(self) -> PostgresArtifactStore:
        """A store over its own pool, as a freshly started process would have."""

        database = Database(TEST_DATABASE_URL or "")
        self._databases.append(database)
        return PostgresArtifactStore(
            WorkspaceArtifactFiles(Workspace(self._root), max_artifact_bytes=10_485_760),
            database,
        )

    def publisher(self) -> ReportPublisher:
        workspace = Workspace(self._root)
        return ReportPublisher(
            ReportTemplateRegistry(), conversation_store(), self.store(), workspace,
        )

    async def shut_down(self) -> None:
        """Dispose every pool this deployment opened."""

        for database in self._databases:
            await database.dispose()
        self._databases.clear()


async def _purge() -> None:
    """Remove this scenario's rows, so a test never sees another run's leftovers."""

    database = Database(TEST_DATABASE_URL or "")
    try:
        async with database.session() as session:
            async with session.begin():
                await session.execute(delete(ArtifactRecord).where(ArtifactRecord.run_id == RUN_ID))
    finally:
        await database.dispose()


@fixture
async def workspace_root(tmp_path):
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    # Purged on the way in as well as out: these assertions are about exactly
    # which artifacts this scenario issued, so a row left behind by an earlier
    # run — or by a developer publishing by hand — would fail them for the
    # wrong reason.
    await _purge()
    yield tmp_path
    await _purge()


@pytest.mark.asyncio
async def test_both_artifacts_are_still_downloadable_after_a_restart(workspace_root) -> None:
    """Publish, shut the deployment down, start another, download both again."""

    # 1. Generate both artifacts.
    original = Deployment(workspace_root)
    published = await original.publisher().publish(
        workspace_id=WORKSPACE_ID, run_id=RUN_ID, template_name=TEMPLATE, formats=["pdf", "docx"], period=PERIOD,
    )

    # 2. Record what was issued.
    recorded = {
        artifact.output_format: {
            "id": artifact.id, "name": artifact.name, "size": artifact.size,
            "sha256": artifact.sha256, "key": artifact.relative_path,
            "media_type": artifact.media_type,
        }
        for artifact in published
    }
    assert set(recorded) == {"pdf", "docx"}
    assert all(entry["size"] > 10_000 for entry in recorded.values())

    # 3. Dispose of the deployment that made them.
    await original.shut_down()
    del original, published

    # 4. Start a fresh one, over a new pool.
    restarted = Deployment(workspace_root)
    try:
        store = restarted.store()

        # 5. Download both again, through the ordinary endpoint.
        user, tenancy = make_artifact_route_caller(workspace_id=WORKSPACE_ID)
        listed = await list_artifacts(
            workspace_id=WORKSPACE_ID, run_id=RUN_ID, user=user, artifact_store=store, tenancy=tenancy,
        )
        assert {item.artifact_id for item in listed} == {
            entry["id"] for entry in recorded.values()
        }

        for document_format, entry in recorded.items():
            record = await store.get(workspace_id=WORKSPACE_ID, artifact_id=entry["id"])
            assert record is not None, f"the {document_format} record did not survive"
            assert record.status is ArtifactStatus.READY
            assert record.relative_path == entry["key"]

            response = await download_artifact(entry["id"], user, store, tenancy)
            assert response.media_type == entry["media_type"]
            assert response.filename == entry["name"]

            # 6. Sizes and hashes are unchanged.
            data = Path(response.path).read_bytes()
            assert len(data) == entry["size"], f"{document_format} changed size"
            assert sha256(data).hexdigest() == entry["sha256"], f"{document_format} changed content"
            assert digest_of(Path(response.path)).sha256 == entry["sha256"]

            # And the bytes are still a readable document of that format.
            if document_format == "pdf":
                reader = PdfReader(str(response.path))
                assert len(reader.pages) >= 2
                text = " ".join(reader.pages[0].extract_text().split())
                assert "Monthly Business Review" in text
            else:
                assert zipfile.is_zipfile(response.path)
                assert Document(str(response.path)).paragraphs
    finally:
        await restarted.shut_down()


@pytest.mark.asyncio
async def test_a_download_link_survives_being_read_by_several_later_deployments(
    workspace_root,
) -> None:
    """The record is durable, not merely cached by whichever store wrote it."""

    original = Deployment(workspace_root)
    published = await original.publisher().publish(
        workspace_id=WORKSPACE_ID, run_id=RUN_ID, template_name=TEMPLATE, formats=["pdf"], period=PERIOD,
    )
    artifact_id, expected = published[0].id, published[0].sha256
    await original.shut_down()

    for _ in range(3):
        deployment = Deployment(workspace_root)
        try:
            path = await deployment.store().path_for(workspace_id=WORKSPACE_ID, artifact_id=artifact_id)
            assert path is not None
            assert digest_of(path).sha256 == expected
        finally:
            await deployment.shut_down()


@pytest.mark.asyncio
async def test_a_missing_file_is_refused_rather_than_served_empty(workspace_root) -> None:
    """A durable record must not outlive its bytes into a successful download."""

    from fastapi import HTTPException

    original = Deployment(workspace_root)
    published = await original.publisher().publish(
        workspace_id=WORKSPACE_ID, run_id=RUN_ID, template_name=TEMPLATE, formats=["pdf"], period=PERIOD,
    )
    artifact_id = published[0].id
    path = await original.store().path_for(workspace_id=WORKSPACE_ID, artifact_id=artifact_id)
    assert path is not None
    path.unlink()
    await original.shut_down()

    restarted = Deployment(workspace_root)
    try:
        store = restarted.store()
        # The record survives, so the loss is visible rather than silent.
        assert await store.get(workspace_id=WORKSPACE_ID, artifact_id=artifact_id) is not None
        assert await store.path_for(workspace_id=WORKSPACE_ID, artifact_id=artifact_id) is None
        user, tenancy = make_artifact_route_caller(workspace_id=WORKSPACE_ID)
        with pytest.raises(HTTPException) as refused:
            await download_artifact(artifact_id, user, store, tenancy)
        assert refused.value.status_code == 404
    finally:
        await restarted.shut_down()
