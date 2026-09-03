"""The delivery HTTP surface: trigger and history, never before ready.

A fake ArtifactStore + fake channel providers stand in for the real
pipeline -- persistence and provider behavior are already proven in
tests/unit/delivery/ and tests/integration/test_delivery_store.py. This suite
is about the API contract: that a non-ready artifact is refused with a clear
error, and that history is listable afterward. Tenant auth is faked via
``tests.support.override_tenant_context`` rather than a real cookie
session -- that flow is already proven end to end by test_auth_api.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.deliveries import router
from app.artifacts.contracts import Artifact, ArtifactStatus
from app.composition import get_delivery_service, get_delivery_store
from app.delivery.contracts import DeliveryAttemptResult
from app.delivery.service import DeliveryService
from tests.support import override_tenant_context

WORKSPACE_ID = uuid4()


def _artifact(artifact_id: str = "artifact-1") -> Artifact:
    return Artifact(
        id=artifact_id, workspace_id=WORKSPACE_ID, name="report.pdf", relative_path=f"artifacts/run/{artifact_id}/report.pdf",
        artifact_type="report_document", media_type="application/pdf", size=2048, sha256="0" * 64,
        status=ArtifactStatus.READY, run_id="run-1", created_at=datetime.now(UTC),
    )


@dataclass
class FakeArtifactStore:
    artifact: Artifact | None

    async def get(self, *, workspace_id, artifact_id: str):
        if self.artifact is None or self.artifact.id != artifact_id or self.artifact.workspace_id != workspace_id:
            return None
        return self.artifact


@dataclass
class FakeDeliveryStore:
    records: dict = field(default_factory=dict)

    async def create(self, *, workspace_id, artifact_id, channel, destination):
        from app.delivery.contracts import DeliveryRecord

        now = datetime.now(UTC)
        record = DeliveryRecord(
            id=uuid4(), workspace_id=workspace_id, artifact_id=artifact_id, channel=channel, destination=destination,
            status="pending", attempt_count=0, last_attempt_at=None, provider_metadata={},
            failure_reason=None, created_at=now, updated_at=now,
        )
        self.records[record.id] = record
        return record

    async def get(self, *, workspace_id, delivery_id):
        record = self.records.get(delivery_id)
        return record if record is not None and record.workspace_id == workspace_id else None

    async def list(self, *, workspace_id, artifact_id=None, status=None):
        items = [item for item in self.records.values() if item.workspace_id == workspace_id]
        if artifact_id is not None:
            items = [item for item in items if item.artifact_id == artifact_id]
        if status is not None:
            items = [item for item in items if item.status == status]
        return items

    async def record_attempt(self, *, workspace_id, delivery_id, status, provider_metadata, failure_reason):
        existing = self.records[delivery_id]
        updated = existing.model_copy(update={
            "status": status, "attempt_count": existing.attempt_count + 1,
            "provider_metadata": provider_metadata, "failure_reason": failure_reason,
        })
        self.records[delivery_id] = updated
        return updated


@dataclass
class FakeProvider:
    async def send(self, *, artifact, destination):
        return DeliveryAttemptResult(success=True, provider_metadata={"link": f"https://x/{artifact.id}"})


def _client(artifact: Artifact | None) -> TestClient:
    artifact_store = FakeArtifactStore(artifact=artifact)
    delivery_store = FakeDeliveryStore()
    service = DeliveryService(artifacts=artifact_store, store=delivery_store, providers={"link": FakeProvider()})

    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides = {
        get_delivery_service: lambda: service,
        get_delivery_store: lambda: delivery_store,
    }
    override_tenant_context(application, workspace_id=WORKSPACE_ID)
    return application, TestClient(application)


def test_create_delivery_for_a_ready_artifact_succeeds() -> None:
    _app, client = _client(_artifact())

    response = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/deliveries", json={"artifact_id": "artifact-1", "channel": "link", "destination": "n/a"})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "sent"
    assert body["provider_metadata"]["link"] == "https://x/artifact-1"


def test_create_delivery_for_a_missing_artifact_is_refused() -> None:
    _app, client = _client(None)

    response = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/deliveries", json={"artifact_id": "artifact-1", "channel": "link", "destination": "n/a"})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "delivery_failed"


def test_create_delivery_for_an_unconfigured_channel_is_refused() -> None:
    _app, client = _client(_artifact())

    response = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/deliveries", json={"artifact_id": "artifact-1", "channel": "email", "destination": "a@b.com"})

    assert response.status_code == 422


def test_list_deliveries_reflects_prior_attempts() -> None:
    _app, client = _client(_artifact())
    client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/deliveries", json={"artifact_id": "artifact-1", "channel": "link", "destination": "n/a"})

    response = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/deliveries", params={"artifact_id": "artifact-1"})

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "sent"


def test_list_deliveries_without_a_filter_returns_everything() -> None:
    _app, client = _client(_artifact())
    client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/deliveries", json={"artifact_id": "artifact-1", "channel": "link", "destination": "n/a"})

    response = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/deliveries")

    assert response.status_code == 200
    assert len(response.json()) == 1
