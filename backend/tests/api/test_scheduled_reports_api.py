"""The scheduled-report HTTP surface: request/response shape and error codes.

In-process fake stores stand in for PostgreSQL -- persistence, claiming and
workspace isolation are already proven against a real database in
tests/integration/test_scheduled_report_store.py. This suite is about the API
contract: status codes, error envelopes, and that creating a schedule for a
require_new_investigation report is refused before any row is written.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.scheduled_reports import router
from app.composition import get_saved_report_store, get_scheduled_report_store
from app.reports.contracts import RelativePeriod, SavedMetricRequest, SavedReportDefinition
from app.scheduling.contracts import ScheduledReportDefinition
from app.scheduling.store import ScheduledReportNotFoundError
from tests.support import override_tenant_context

WORKSPACE_ID = uuid4()


def _now() -> datetime:
    return datetime.now(UTC)


def _saved_report(**overrides) -> SavedReportDefinition:
    now = datetime.now(UTC)
    fields = dict(
        id=uuid4(), workspace_id=WORKSPACE_ID, owner=None, name="Weekly Revenue", description=None,
        template_id="analysis_summary", template_version="4",
        metric_requests=[SavedMetricRequest(metric="revenue")],
        default_period=RelativePeriod(kind="last_n_days", days=7),
        narrative_policy="exclude", seed_run_id=None, seed_narrative=None, seed_narrative_period=None,
        version=1, status="active", created_at=now, updated_at=now,
    )
    fields.update(overrides)
    return SavedReportDefinition(**fields)


@dataclass
class FakeSavedReportStore:
    reports: dict[UUID, SavedReportDefinition] = field(default_factory=dict)

    async def get(self, *, workspace_id, saved_report_id):
        report = self.reports.get(saved_report_id)
        return report if report is not None and report.workspace_id == workspace_id else None


@dataclass
class FakeScheduledReportStore:
    schedules: dict[UUID, ScheduledReportDefinition] = field(default_factory=dict)

    async def create(self, *, saved_report_id, workspace_id, schedule, timezone, formats,
                      delivery_channel, delivery_destination, next_run_at):
        now = _now()
        definition = ScheduledReportDefinition(
            id=uuid4(), saved_report_id=saved_report_id, workspace_id=workspace_id, schedule=schedule,
            timezone=timezone, formats=formats, delivery_channel=delivery_channel,
            delivery_destination=delivery_destination, enabled=True, next_run_at=next_run_at,
            last_run_at=None, last_result=None, consecutive_failures=0, created_at=now, updated_at=now,
        )
        self.schedules[definition.id] = definition
        return definition

    async def get(self, *, workspace_id, scheduled_report_id):
        item = self.schedules.get(scheduled_report_id)
        return item if item is not None and item.workspace_id == workspace_id else None

    async def list(self, *, workspace_id, enabled, limit, offset):
        items = [item for item in self.schedules.values() if item.workspace_id == workspace_id]
        if enabled is not None:
            items = [item for item in items if item.enabled == enabled]
        return items[offset:offset + limit], len(items)

    async def update(self, *, workspace_id, scheduled_report_id, changes: dict[str, Any]):
        item = self.schedules.get(scheduled_report_id)
        if item is None or item.workspace_id != workspace_id:
            raise ScheduledReportNotFoundError(str(scheduled_report_id))
        merged = item.model_dump()
        if "schedule" in changes:
            merged["schedule"] = changes["schedule"].model_dump()
        for key in ("timezone", "formats", "delivery_channel", "delivery_destination", "enabled", "next_run_at"):
            if key in changes:
                merged[key] = changes[key]
        updated = ScheduledReportDefinition.model_validate(merged)
        self.schedules[scheduled_report_id] = updated
        return updated


def _client(
    saved_reports: FakeSavedReportStore, schedules: FakeScheduledReportStore, *, workspace_id: UUID = WORKSPACE_ID,
) -> TestClient:
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides = {
        get_saved_report_store: lambda: saved_reports,
        get_scheduled_report_store: lambda: schedules,
    }
    override_tenant_context(application, workspace_id=workspace_id)
    return TestClient(application)


def _create_body(saved_report_id: str, **overrides) -> dict:
    body = {
        "saved_report_id": saved_report_id,
        "schedule": {"kind": "daily", "hour": 6, "minute": 0},
        "timezone": "UTC",
        "formats": ["pdf"],
    }
    body.update(overrides)
    return body


def test_create_computes_next_run_at_and_returns_the_schedule() -> None:
    saved = _saved_report()
    client = _client(FakeSavedReportStore(reports={saved.id: saved}), FakeScheduledReportStore())

    response = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/scheduled", json=_create_body(str(saved.id)))

    assert response.status_code == 201
    body = response.json()
    assert body["saved_report_id"] == str(saved.id)
    assert body["enabled"] is True
    assert body["next_run_at"] > datetime.now(UTC).isoformat()


def test_create_is_404_for_an_unknown_saved_report() -> None:
    client = _client(FakeSavedReportStore(), FakeScheduledReportStore())

    response = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/scheduled", json=_create_body(str(uuid4())))

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "unknown_saved_report"


def test_create_refuses_a_require_new_investigation_report() -> None:
    saved = _saved_report(narrative_policy="require_new_investigation")
    client = _client(FakeSavedReportStore(reports={saved.id: saved}), FakeScheduledReportStore())

    response = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/scheduled", json=_create_body(str(saved.id)))

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "requires_new_investigation"


def test_create_is_404_across_workspaces() -> None:
    other_workspace_id = uuid4()
    saved = _saved_report(workspace_id=other_workspace_id)
    client = _client(FakeSavedReportStore(reports={saved.id: saved}), FakeScheduledReportStore())

    response = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/scheduled", json=_create_body(str(saved.id)))

    assert response.status_code == 404


def test_delivery_channel_without_destination_is_rejected() -> None:
    saved = _saved_report()
    client = _client(FakeSavedReportStore(reports={saved.id: saved}), FakeScheduledReportStore())

    response = client.post(
        f"/api/v1/workspaces/{WORKSPACE_ID}/reports/scheduled", json={**_create_body(str(saved.id)), "delivery_channel": "webhook"},
    )

    assert response.status_code == 422


def test_list_and_get_round_trip() -> None:
    saved = _saved_report()
    client = _client(FakeSavedReportStore(reports={saved.id: saved}), FakeScheduledReportStore())
    created = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/scheduled", json=_create_body(str(saved.id))).json()

    listed = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/scheduled").json()
    fetched = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/scheduled/{created['id']}").json()

    assert listed["total"] == 1
    assert fetched["id"] == created["id"]


def test_get_is_404_for_an_unknown_id() -> None:
    client = _client(FakeSavedReportStore(), FakeScheduledReportStore())

    response = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/scheduled/{uuid4()}")

    assert response.status_code == 404


def test_patch_can_disable_a_schedule() -> None:
    saved = _saved_report()
    client = _client(FakeSavedReportStore(reports={saved.id: saved}), FakeScheduledReportStore())
    created = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/scheduled", json=_create_body(str(saved.id))).json()

    response = client.patch(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/scheduled/{created['id']}", json={"enabled": False})

    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_patch_changing_the_schedule_recomputes_next_run_at() -> None:
    saved = _saved_report()
    client = _client(FakeSavedReportStore(reports={saved.id: saved}), FakeScheduledReportStore())
    created = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/scheduled", json=_create_body(str(saved.id))).json()

    response = client.patch(
        f"/api/v1/workspaces/{WORKSPACE_ID}/reports/scheduled/{created['id']}",
        json={"schedule": {"kind": "weekly", "day_of_week": 0, "hour": 9, "minute": 0}, "timezone": "America/New_York"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schedule"]["kind"] == "weekly"
    assert body["next_run_at"] != created["next_run_at"]


def test_patch_is_404_for_an_unknown_id() -> None:
    client = _client(FakeSavedReportStore(), FakeScheduledReportStore())

    response = client.patch(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/scheduled/{uuid4()}", json={"enabled": False})

    assert response.status_code == 404


def test_patch_with_a_mismatched_delivery_pair_is_rejected() -> None:
    saved = _saved_report()
    client = _client(FakeSavedReportStore(reports={saved.id: saved}), FakeScheduledReportStore())
    created = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/scheduled", json=_create_body(str(saved.id))).json()

    response = client.patch(
        f"/api/v1/workspaces/{WORKSPACE_ID}/reports/scheduled/{created['id']}", json={"delivery_destination": "https://example.com/hook"},
    )

    assert response.status_code == 422
