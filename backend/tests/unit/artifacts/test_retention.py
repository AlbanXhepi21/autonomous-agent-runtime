"""Expiring artifacts: claim, delete, preserve the audit row, retry, give up."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.artifacts.contracts import ArtifactStatus
from app.artifacts.files import WorkspaceArtifactFiles
from app.artifacts.retention import RetentionWorker
from app.artifacts.store import WorkspaceArtifactStore
from app.environment.workspace import Workspace


@pytest.fixture
def rig(tmp_path):
    workspace = Workspace(tmp_path)
    files = WorkspaceArtifactFiles(workspace, max_artifact_bytes=10_485_760)
    store = WorkspaceArtifactStore(workspace, files=files)
    return workspace, files, store


async def _register(store, files, workspace, *, name: str, expires_at=None, retention_policy="standard"):
    source = workspace.root / name
    source.write_bytes(b"content")
    return await store.register(
        run_id="retention-test-run", source_path=name, name=name, media_type="application/pdf",
        expires_at=expires_at, retention_policy=retention_policy,
    )


@pytest.mark.asyncio
async def test_an_expired_ready_artifact_is_deleted(rig) -> None:
    workspace, files, store = rig
    now = datetime.now(UTC)
    artifact = await _register(store, files, workspace, name="a.pdf", expires_at=now - timedelta(hours=1))
    worker = RetentionWorker(artifacts=store, files=files)

    outcomes = await worker.run_once()

    assert len(outcomes) == 1
    assert outcomes[0].status == "deleted"
    assert files.path(artifact.relative_path) is None


@pytest.mark.asyncio
async def test_the_record_survives_as_an_audit_trail(rig) -> None:
    workspace, files, store = rig
    now = datetime.now(UTC)
    artifact = await _register(store, files, workspace, name="a.pdf", expires_at=now - timedelta(hours=1))
    worker = RetentionWorker(artifacts=store, files=files)

    await worker.run_once()

    record = store._artifacts[artifact.id]  # the in-memory row, not the serving API
    assert record.status is ArtifactStatus.DELETED
    assert record.deleted_at is not None
    assert record.name == "a.pdf"
    assert record.size == artifact.size
    assert record.sha256 == artifact.sha256


@pytest.mark.asyncio
async def test_a_deleted_artifact_is_no_longer_servable(rig) -> None:
    workspace, files, store = rig
    now = datetime.now(UTC)
    artifact = await _register(store, files, workspace, name="a.pdf", expires_at=now - timedelta(hours=1))
    worker = RetentionWorker(artifacts=store, files=files)

    await worker.run_once()

    assert await store.get(artifact.id) is None


@pytest.mark.asyncio
async def test_a_not_yet_expired_artifact_is_untouched(rig) -> None:
    workspace, files, store = rig
    now = datetime.now(UTC)
    artifact = await _register(store, files, workspace, name="a.pdf", expires_at=now + timedelta(days=1))
    worker = RetentionWorker(artifacts=store, files=files)

    outcomes = await worker.run_once()

    assert outcomes == []
    assert await store.get(artifact.id) is not None


@pytest.mark.asyncio
async def test_an_artifact_with_no_expiry_is_never_claimed(rig) -> None:
    workspace, files, store = rig
    artifact = await _register(store, files, workspace, name="a.pdf", expires_at=None)
    worker = RetentionWorker(artifacts=store, files=files)

    outcomes = await worker.run_once()

    assert outcomes == []
    assert await store.get(artifact.id) is not None


@pytest.mark.asyncio
async def test_legal_hold_is_never_claimed_even_when_expired(rig) -> None:
    workspace, files, store = rig
    now = datetime.now(UTC)
    artifact = await _register(
        store, files, workspace, name="a.pdf", expires_at=now - timedelta(hours=1), retention_policy="legal_hold",
    )
    worker = RetentionWorker(artifacts=store, files=files)

    outcomes = await worker.run_once()

    assert outcomes == []
    assert await store.get(artifact.id) is not None


@pytest.mark.asyncio
async def test_permanent_is_never_claimed_even_when_expired(rig) -> None:
    workspace, files, store = rig
    now = datetime.now(UTC)
    artifact = await _register(
        store, files, workspace, name="a.pdf", expires_at=now - timedelta(hours=1), retention_policy="permanent",
    )
    worker = RetentionWorker(artifacts=store, files=files)

    outcomes = await worker.run_once()

    assert outcomes == []
    assert await store.get(artifact.id) is not None


@pytest.mark.asyncio
async def test_deleting_an_already_deleted_artifact_is_a_no_op(rig) -> None:
    """Idempotent deletion: running the worker twice never double-processes a row."""

    workspace, files, store = rig
    now = datetime.now(UTC)
    await _register(store, files, workspace, name="a.pdf", expires_at=now - timedelta(hours=1))
    worker = RetentionWorker(artifacts=store, files=files)

    first = await worker.run_once()
    second = await worker.run_once()

    assert len(first) == 1 and first[0].status == "deleted"
    assert second == []


@pytest.mark.asyncio
async def test_a_transient_deletion_failure_is_retried_on_a_later_run(rig, monkeypatch) -> None:
    workspace, files, store = rig
    now = datetime.now(UTC)
    artifact = await _register(store, files, workspace, name="a.pdf", expires_at=now - timedelta(hours=1))

    def boom(key: str) -> None:
        raise OSError("disk is temporarily unavailable")

    monkeypatch.setattr(files, "discard", boom)
    worker = RetentionWorker(artifacts=store, files=files, max_attempts=5)

    outcomes = await worker.run_once()

    assert outcomes[0].status == "failed"
    record = store._artifacts[artifact.id]
    assert record.status is ArtifactStatus.READY  # still there, still retryable
    assert record.deletion_attempts == 1
    assert record.deletion_claimed_at is None  # released, not stuck claimed forever


@pytest.mark.asyncio
async def test_exhausting_max_attempts_stops_reclaiming_the_row(rig, monkeypatch) -> None:
    workspace, files, store = rig
    now = datetime.now(UTC)
    artifact = await _register(store, files, workspace, name="a.pdf", expires_at=now - timedelta(hours=1))

    def boom(key: str) -> None:
        raise OSError("disk is permanently unavailable")

    monkeypatch.setattr(files, "discard", boom)
    worker = RetentionWorker(artifacts=store, files=files, max_attempts=2)

    first = await worker.run_once()
    second = await worker.run_once()
    third = await worker.run_once()

    assert first[0].status == "failed"
    assert second[0].status == "gave_up"
    assert third == []  # excluded from claiming once max_attempts is reached
    record = store._artifacts[artifact.id]
    assert record.status is ArtifactStatus.READY  # the row is never silently dropped
    assert record.deletion_attempts == 2


@pytest.mark.asyncio
async def test_a_stale_claim_is_reclaimable(rig) -> None:
    workspace, files, store = rig
    now = datetime.now(UTC)
    await _register(store, files, workspace, name="a.pdf", expires_at=now - timedelta(hours=1))
    worker = RetentionWorker(artifacts=store, files=files, stale_claim_after=timedelta(seconds=0))

    # Simulate a worker that claimed the row and then crashed before finishing.
    await store.claim_expired(now=now, stale_after=timedelta(minutes=15), limit=10)

    outcomes = await worker.run_once()

    assert len(outcomes) == 1 and outcomes[0].status == "deleted"


@pytest.mark.asyncio
async def test_a_freshly_claimed_row_is_not_reclaimed_by_a_second_worker(rig) -> None:
    workspace, files, store = rig
    now = datetime.now(UTC)
    await _register(store, files, workspace, name="a.pdf", expires_at=now - timedelta(hours=1))

    first_claim = await store.claim_expired(now=now, stale_after=timedelta(minutes=15), limit=10)
    second_claim = await store.claim_expired(now=now, stale_after=timedelta(minutes=15), limit=10)

    assert len(first_claim) == 1
    assert second_claim == []
