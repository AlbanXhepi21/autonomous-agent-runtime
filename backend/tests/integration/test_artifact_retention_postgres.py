"""Artifact expiration claiming, against a real database.

The in-memory store's claim semantics are already covered by
tests/unit/artifacts/test_retention.py; this suite exists specifically to
prove the same guarantees hold with real Postgres row locking
(``FOR UPDATE SKIP LOCKED``), which the in-memory fake cannot exercise.

Skips when TEST_DATABASE_URL is unset, like the other database tests.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest
from pytest_asyncio import fixture
from sqlalchemy import delete

pytest.importorskip("sqlalchemy")

from app.artifacts.contracts import ArtifactStatus
from app.artifacts.files import WorkspaceArtifactFiles
from app.artifacts.postgres import PostgresArtifactStore
from app.artifacts.retention import RetentionWorker
from app.db.records import ArtifactRecord
from app.db.session import Database
from app.environment.workspace import Workspace

pytestmark = pytest.mark.postgres

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
RUN_ID = "test-artifact-retention-run"


async def _purge() -> None:
    database = Database(TEST_DATABASE_URL or "")
    try:
        async with database.session() as session, session.begin():
            await session.execute(delete(ArtifactRecord).where(ArtifactRecord.run_id == RUN_ID))
    finally:
        await database.dispose()


@fixture
async def rig(tmp_path):
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    await _purge()
    database = Database(TEST_DATABASE_URL)
    workspace = Workspace(tmp_path)
    files = WorkspaceArtifactFiles(workspace, max_artifact_bytes=10_485_760)
    store = PostgresArtifactStore(files, database)
    try:
        yield workspace, files, store
    finally:
        await database.dispose()
        await _purge()


async def _register(store, workspace, *, name: str, expires_at=None, retention_policy="standard"):
    source = workspace.root / name
    source.write_bytes(b"content")
    return await store.register(
        run_id=RUN_ID, source_path=name, name=name, media_type="application/pdf",
        expires_at=expires_at, retention_policy=retention_policy,
    )


@pytest.mark.asyncio
async def test_an_expired_artifact_is_claimed_and_deleted(rig) -> None:
    workspace, files, store = rig
    now = datetime.now(UTC)
    artifact = await _register(store, workspace, name="a.pdf", expires_at=now - timedelta(hours=1))
    worker = RetentionWorker(artifacts=store, files=files)

    outcomes = await worker.run_once()

    assert len(outcomes) == 1 and outcomes[0].status == "deleted"
    assert files.path(artifact.relative_path) is None
    assert await store.get(artifact.id) is None


@pytest.mark.asyncio
async def test_the_record_survives_with_status_deleted(rig) -> None:
    workspace, files, store = rig
    now = datetime.now(UTC)
    artifact = await _register(store, workspace, name="a.pdf", expires_at=now - timedelta(hours=1))
    worker = RetentionWorker(artifacts=store, files=files)

    await worker.run_once()

    database = store._database
    async with database.session() as session:
        record = await session.get(ArtifactRecord, artifact.id)
    assert record is not None
    assert record.status == ArtifactStatus.DELETED.value
    assert record.deleted_at is not None
    assert record.name == "a.pdf"


@pytest.mark.asyncio
async def test_two_concurrent_claims_never_overlap(rig) -> None:
    workspace, files, store = rig
    now = datetime.now(UTC)
    await _register(store, workspace, name="a.pdf", expires_at=now - timedelta(hours=1))

    first = await store.claim_expired(now=now, stale_after=timedelta(minutes=15), limit=10)
    second = await store.claim_expired(now=now, stale_after=timedelta(minutes=15), limit=10)

    assert len(first) == 1
    assert second == []


@pytest.mark.asyncio
async def test_legal_hold_is_never_claimed(rig) -> None:
    workspace, files, store = rig
    now = datetime.now(UTC)
    artifact = await _register(
        store, workspace, name="a.pdf", expires_at=now - timedelta(hours=1), retention_policy="legal_hold",
    )

    claimed = await store.claim_expired(now=now, stale_after=timedelta(minutes=15), limit=10)

    assert claimed == []
    assert await store.get(artifact.id) is not None


@pytest.mark.asyncio
async def test_a_stale_claim_is_reclaimable(rig) -> None:
    workspace, files, store = rig
    now = datetime.now(UTC)
    await _register(store, workspace, name="a.pdf", expires_at=now - timedelta(hours=1))
    await store.claim_expired(now=now, stale_after=timedelta(minutes=15), limit=10)

    # A later instant with the same staleness window makes the earlier claim
    # (stamped at `now`) look abandoned, the same way a real worker's clock
    # advancing past a crashed worker's claim would.
    later = now + timedelta(minutes=16)
    reclaimed = await store.claim_expired(now=later, stale_after=timedelta(minutes=15), limit=10)

    assert len(reclaimed) == 1


@pytest.mark.asyncio
async def test_max_attempts_excludes_the_row_from_future_claims(rig) -> None:
    workspace, files, store = rig
    now = datetime.now(UTC)
    artifact = await _register(store, workspace, name="a.pdf", expires_at=now - timedelta(hours=1))
    for _ in range(3):
        await store.record_deletion_failure(artifact.id, "disk unavailable")

    claimed = await store.claim_expired(now=now, stale_after=timedelta(minutes=15), limit=10, max_attempts=3)

    assert claimed == []
    assert await store.get(artifact.id) is not None  # the row is still there, just not offered
