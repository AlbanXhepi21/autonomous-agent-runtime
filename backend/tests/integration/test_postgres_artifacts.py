"""Optional integration coverage for durable PostgreSQL artifact records.

The point of the PostgreSQL registry is that a download link outlives the
process that issued it, and that cannot be shown by a store which answers from
its own memory. Every retrieval here therefore goes through a store built after
the one that registered the artifact was discarded, over a fresh connection
pool — the closest a test gets to restarting the application.
"""

import os
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from pytest_asyncio import fixture

pytest.importorskip("sqlalchemy")

from sqlalchemy import delete, select

from app.analytics.presentation.templates import ReportTemplateRegistry
from app.api.routes.artifacts import download_artifact
from app.artifacts.contracts import ArtifactStatus
from app.artifacts.files import WorkspaceArtifactFiles, digest_of
from app.artifacts.postgres import PostgresArtifactStore
from app.db.records import ArtifactRecord
from app.db.session import Database
from app.environment.workspace import Workspace
from app.orchestration.publishing import ReportPublisher
from tests.support import make_artifact_route_caller

pytestmark = pytest.mark.postgres

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
#: The legacy workspace seeded by migration 20260903_0016 -- always present,
#: so single-tenant tests can use it as a valid FK target without minting rows.
WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000001")

CHART = {
    "id": "chart-1", "type": "bar", "title": "Revenue by category", "x_field": "category",
    "y_fields": ["revenue"], "series": [], "kpis": [],
    "data": [{"category": "Electronics", "revenue": 163}, {"category": "Fashion", "revenue": 63}],
    "source_query_ids": ["query_003"], "formatting": {"show_legend": True},
}


async def _value(value: object) -> object:
    return value


def _conversation_store(run_id: str):
    """The finished run a publisher reads, without a database behind it."""

    run = SimpleNamespace(id=run_id, status="completed", chart_specs=[CHART],
                          answer_sources=[{"id": "query_003", "kind": "database_query",
                                           "run_id": run_id, "label": "Revenue by category",
                                           "referenced_tables": ["orders"], "row_count": 2,
                                           "truncated": False, "executed_at": None}],
                          created_at=datetime.now(UTC))
    return SimpleNamespace(
        get_run=lambda *, workspace_id, run_id: _value(run),
        get_assistant_message_for_run=lambda *, workspace_id, run_id: _value(
            SimpleNamespace(content="## Finding\nRevenue grew 18%.")
        ),
    )


class Registry:
    """Build a store over a *new* pool each time, so nothing is answered from memory."""

    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace
        self._databases: list[Database] = []

    def database(self) -> Database:
        database = Database(TEST_DATABASE_URL or "")
        self._databases.append(database)
        return database

    def store(self) -> PostgresArtifactStore:
        return PostgresArtifactStore(
            WorkspaceArtifactFiles(self._workspace, max_artifact_bytes=10_485_760),
            self.database(),
        )

    async def dispose(self) -> None:
        for database in self._databases:
            await database.dispose()


@fixture
async def registry(tmp_path):
    """Connect to an already-migrated test database; never create its schema."""

    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    built = Registry(Workspace(tmp_path))
    try:
        yield built
    finally:
        await built.dispose()


async def _statuses(run_id: str) -> list[str]:
    """Read the raw rows, including the ones retrieval deliberately hides."""

    database = Database(TEST_DATABASE_URL or "")
    try:
        async with database.session() as session:
            records = (await session.scalars(
                select(ArtifactRecord).where(ArtifactRecord.run_id == run_id)
            )).all()
            return [record.status for record in records]
    finally:
        await database.dispose()


async def _purge(run_id: str) -> None:
    database = Database(TEST_DATABASE_URL or "")
    try:
        async with database.session() as session:
            async with session.begin():
                await session.execute(delete(ArtifactRecord).where(ArtifactRecord.run_id == run_id))
    finally:
        await database.dispose()


@pytest.mark.asyncio
async def test_published_documents_are_retrievable_from_a_later_store(registry, tmp_path) -> None:
    """Publish PDF and DOCX, discard everything, then read both back."""

    run_id = f"artifact-test-{uuid4()}"
    workspace = Workspace(tmp_path)
    publisher = ReportPublisher(
        ReportTemplateRegistry(), _conversation_store(run_id), registry.store(), workspace,
    )
    try:
        published = await publisher.publish(
            workspace_id=WORKSPACE_ID, run_id=run_id, template_name="monthly_business_review",
            formats=["pdf", "docx"], period="August 2026",
        )
        assert [item.output_format for item in published] == ["pdf", "docx"]
        assert all(item.status is ArtifactStatus.READY for item in published)
        assert all(item.template_id == "monthly_business_review" for item in published)
        assert all(item.template_version for item in published)

        # Everything that registered these artifacts is now gone. A store built
        # afterwards knows about them only because PostgreSQL does.
        del publisher
        later = registry.store()

        for original in published:
            record = await later.get(workspace_id=WORKSPACE_ID, artifact_id=original.id)
            assert record is not None, f"{original.output_format} record did not survive"
            assert record.relative_path == original.relative_path
            assert (record.size, record.sha256) == (original.size, original.sha256)
            assert record.media_type == original.media_type

            path = await later.path_for(workspace_id=WORKSPACE_ID, artifact_id=original.id)
            assert path is not None and path.is_file()
            downloaded = path.read_bytes()
            assert len(downloaded) == record.size
            assert digest_of(path).sha256 == record.sha256

        listed = await later.list(workspace_id=WORKSPACE_ID, run_id=run_id)
        assert {item.output_format for item in listed} == {"pdf", "docx"}

        # The download endpoint serves them from a store it did not publish with.
        user, tenancy = make_artifact_route_caller(workspace_id=WORKSPACE_ID)
        for original in published:
            response = await download_artifact(original.id, user, registry.store(), tenancy)
            assert response.media_type == original.media_type
            assert response.path.read_bytes() == (await later.path_for(workspace_id=WORKSPACE_ID, artifact_id=original.id)).read_bytes()
    finally:
        await _purge(run_id)


@pytest.mark.asyncio
async def test_a_record_without_its_bytes_refuses_to_resolve(registry, tmp_path) -> None:
    """A vanished file must not become a successful download of nothing."""

    run_id = f"artifact-test-{uuid4()}"
    (tmp_path / "report.md").write_text("# Report\n")
    try:
        artifact = await registry.store().register(workspace_id=WORKSPACE_ID, run_id=run_id, source_path="report.md")
        path = await registry.store().path_for(workspace_id=WORKSPACE_ID, artifact_id=artifact.id)
        assert path is not None
        path.unlink()

        later = registry.store()
        assert await later.get(workspace_id=WORKSPACE_ID, artifact_id=artifact.id) is not None
        assert await later.path_for(workspace_id=WORKSPACE_ID, artifact_id=artifact.id) is None
    finally:
        await _purge(run_id)


@pytest.mark.asyncio
async def test_runs_remain_isolated_across_store_instances(registry, tmp_path) -> None:
    first_run, second_run = f"artifact-test-{uuid4()}", f"artifact-test-{uuid4()}"
    (tmp_path / "one.txt").write_text("one")
    (tmp_path / "two.txt").write_text("two")
    try:
        first = await registry.store().register(workspace_id=WORKSPACE_ID, run_id=first_run, source_path="one.txt")
        second = await registry.store().register(workspace_id=WORKSPACE_ID, run_id=second_run, source_path="two.txt")

        later = registry.store()
        assert [item.id for item in await later.list(workspace_id=WORKSPACE_ID, run_id=first_run)] == [first.id]
        assert [item.id for item in await later.list(workspace_id=WORKSPACE_ID, run_id=second_run)] == [second.id]
        assert first.relative_path.startswith(f"artifacts/{first_run}/")
        assert second.relative_path.startswith(f"artifacts/{second_run}/")
    finally:
        await _purge(first_run)
        await _purge(second_run)


@pytest.mark.asyncio
async def test_a_failed_write_is_recorded_but_never_handed_out(registry, tmp_path) -> None:
    run_id = f"artifact-test-{uuid4()}"
    (tmp_path / "report.md").write_text("# Report\n")

    class FailingFiles(WorkspaceArtifactFiles):
        def write(self, key: str, source):
            raise OSError("disk full")

    store = registry.store()
    failing = PostgresArtifactStore(
        FailingFiles(Workspace(tmp_path), max_artifact_bytes=10_485_760), registry.database()
    )
    try:
        with pytest.raises(ValueError, match="could not be written"):
            await failing.register(workspace_id=WORKSPACE_ID, run_id=run_id, source_path="report.md")

        # Nothing is retrievable, from this store or any later one.
        assert await store.list(workspace_id=WORKSPACE_ID, run_id=run_id) == []
        assert await registry.store().list(workspace_id=WORKSPACE_ID, run_id=run_id) == []

        # The row itself remains, marked failed, so the attempt stays visible.
        assert await _statuses(run_id) == [ArtifactStatus.FAILED.value]
    finally:
        await _purge(run_id)
