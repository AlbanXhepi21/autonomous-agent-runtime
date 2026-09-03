"""DeliveryService: the ready-only gate, retry, and what gets persisted."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.artifacts.contracts import Artifact, ArtifactStatus
from app.delivery.contracts import DeliveryAttemptResult, DeliveryError, DeliveryRecord
from app.delivery.service import DeliveryService
from app.reliability.contracts import FailureCategory
from app.reliability.retry import RetryPolicy, RetryRule

WORKSPACE_ID = uuid4()


def _artifact() -> Artifact:
    return Artifact(
        id="artifact-1", workspace_id=WORKSPACE_ID, name="report.pdf", relative_path="artifacts/run/artifact-1/report.pdf",
        artifact_type="report_document", media_type="application/pdf", size=4096, sha256="0" * 64,
        status=ArtifactStatus.READY, run_id="run-1", created_at=datetime.now(UTC),
    )


@dataclass
class FakeArtifactStore:
    """Only .get() is used by DeliveryService -- and only READY should ever come back."""

    artifact: Artifact | None

    async def get(self, *, workspace_id, artifact_id: str) -> Artifact | None:
        return self.artifact if self.artifact and self.artifact.id == artifact_id else None


@dataclass
class FakeDeliveryStore:
    records: dict[UUID, DeliveryRecord] = field(default_factory=dict)
    attempts: list[dict] = field(default_factory=list)

    async def create(self, *, workspace_id, artifact_id, channel, destination):
        now = datetime.now(UTC)
        record = DeliveryRecord(
            id=uuid4(), workspace_id=workspace_id, artifact_id=artifact_id, channel=channel, destination=destination,
            status="pending", attempt_count=0, last_attempt_at=None, provider_metadata={},
            failure_reason=None, created_at=now, updated_at=now,
        )
        self.records[record.id] = record
        return record

    async def record_attempt(self, *, workspace_id, delivery_id, status, provider_metadata, failure_reason):
        self.attempts.append({"delivery_id": delivery_id, "status": status, "failure_reason": failure_reason})
        existing = self.records[delivery_id]
        updated = existing.model_copy(update={
            "status": status, "attempt_count": existing.attempt_count + 1,
            "provider_metadata": provider_metadata, "failure_reason": failure_reason,
            "last_attempt_at": datetime.now(UTC),
        })
        self.records[delivery_id] = updated
        return updated


@dataclass
class FakeProvider:
    outcomes: list[DeliveryAttemptResult]
    calls: list[tuple] = field(default_factory=list)

    async def send(self, *, artifact, destination):
        self.calls.append((artifact.id, destination))
        return self.outcomes.pop(0)


async def _no_sleep(delay: float) -> None:
    return None


_UNSET = object()


def _service(*, artifact=_UNSET, providers=None, retry_policy=None) -> tuple[DeliveryService, FakeDeliveryStore]:
    store = FakeDeliveryStore()
    resolved = _artifact() if artifact is _UNSET else artifact
    service = DeliveryService(
        artifacts=FakeArtifactStore(artifact=resolved), store=store,
        providers=providers or {}, retry_policy=retry_policy, sleep=_no_sleep,
    )
    return service, store


@pytest.mark.asyncio
async def test_delivering_a_ready_artifact_succeeds() -> None:
    provider = FakeProvider(outcomes=[DeliveryAttemptResult(success=True, provider_metadata={"link": "https://x"})])
    service, store = _service(providers={"link": provider})

    record = await service.deliver(workspace_id=WORKSPACE_ID, artifact_id="artifact-1", channel="link", destination="unused")

    assert record.status == "sent"
    assert record.attempt_count == 1
    assert provider.calls == [("artifact-1", "unused")]


@pytest.mark.asyncio
async def test_a_missing_artifact_is_refused_before_any_provider_is_called() -> None:
    provider = FakeProvider(outcomes=[])
    service, _store = _service(artifact=None, providers={"link": provider})

    with pytest.raises(DeliveryError):
        await service.deliver(workspace_id=WORKSPACE_ID, artifact_id="artifact-1", channel="link", destination="unused")

    assert provider.calls == []


@pytest.mark.asyncio
async def test_an_unconfigured_channel_is_refused() -> None:
    service, _store = _service(providers={})

    with pytest.raises(DeliveryError, match="not configured"):
        await service.deliver(workspace_id=WORKSPACE_ID, artifact_id="artifact-1", channel="email", destination="a@b.com")


@pytest.mark.asyncio
async def test_a_transient_failure_is_retried_then_succeeds() -> None:
    provider = FakeProvider(outcomes=[
        DeliveryAttemptResult(success=False, retryable=True, failure_reason="timeout"),
        DeliveryAttemptResult(success=True, provider_metadata={"status_code": 200}),
    ])
    policy = RetryPolicy({("delivery", FailureCategory.DELIVERY_FAILURE): RetryRule(max_attempts=3, initial_delay_seconds=0, max_delay_seconds=0)})
    service, store = _service(providers={"webhook": provider}, retry_policy=policy)

    record = await service.deliver(workspace_id=WORKSPACE_ID, artifact_id="artifact-1", channel="webhook", destination="https://x")

    assert record.status == "sent"
    assert record.attempt_count == 2
    assert len(store.attempts) == 2
    assert store.attempts[0]["status"] == "failed"
    assert store.attempts[1]["status"] == "sent"


@pytest.mark.asyncio
async def test_exhausting_retries_persists_a_final_failed_record_with_every_attempt_counted() -> None:
    provider = FakeProvider(outcomes=[
        DeliveryAttemptResult(success=False, retryable=True, failure_reason="timeout"),
        DeliveryAttemptResult(success=False, retryable=True, failure_reason="timeout"),
        DeliveryAttemptResult(success=False, retryable=True, failure_reason="timeout"),
    ])
    policy = RetryPolicy({("delivery", FailureCategory.DELIVERY_FAILURE): RetryRule(max_attempts=3, initial_delay_seconds=0, max_delay_seconds=0)})
    service, store = _service(providers={"webhook": provider}, retry_policy=policy)

    record = await service.deliver(workspace_id=WORKSPACE_ID, artifact_id="artifact-1", channel="webhook", destination="https://x")

    assert record.status == "failed"
    assert record.attempt_count == 3
    assert record.failure_reason == "timeout"


@pytest.mark.asyncio
async def test_a_non_retryable_failure_is_recorded_immediately_without_retrying() -> None:
    provider = FakeProvider(outcomes=[
        DeliveryAttemptResult(success=False, retryable=False, failure_reason="webhook responded 404"),
    ])
    service, store = _service(providers={"webhook": provider})

    record = await service.deliver(workspace_id=WORKSPACE_ID, artifact_id="artifact-1", channel="webhook", destination="https://x")

    assert record.status == "failed"
    assert record.attempt_count == 1
    assert len(provider.calls) == 1
