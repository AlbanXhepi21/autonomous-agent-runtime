"""The saved-report HTTP surface: request/response shape and error codes.

An in-process fake store stands in for PostgreSQL here -- persistence itself,
workspace isolation and optimistic concurrency are already proven against a
real database in ``tests/integration/test_saved_report_store.py``. This suite
is about what the API contract looks like: status codes, error envelopes, and
that the deterministic execution path never needs a database at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.analytics.presentation.templates import ReportTemplateRegistry
from app.api.routes.reports import router
from app.artifacts.store import WorkspaceArtifactStore
from app.composition import (
    get_artifact_store,
    get_report_template_registry,
    get_saved_report_execution_service,
    get_saved_report_store,
)
from app.environment.workspace import Workspace
from app.reports.contracts import SavedReportDefinition, SavedReportExecution
from app.reports.execution import SavedReportExecutionService
from app.reports.store import (
    SavedReportNotFoundError,
    SavedReportStore,
    SavedReportVersionConflictError,
)
from tests.support import override_tenant_context

WORKSPACE_ID = uuid4()


@dataclass
class FakeSavedReportStore(SavedReportStore):
    """An in-process stand-in with the same isolation and versioning rules."""

    reports: dict[UUID, SavedReportDefinition] = field(default_factory=dict)
    executions: dict[str, SavedReportExecution] = field(default_factory=dict)

    async def create(self, **kwargs: Any) -> SavedReportDefinition:
        now = datetime.now(UTC)
        definition = SavedReportDefinition(id=uuid4(), version=1, status="active",
                                           created_at=now, updated_at=now, **kwargs)
        self.reports[definition.id] = definition
        return definition

    async def list(self, *, workspace_id, status, limit, offset):
        items = [item for item in self.reports.values() if item.workspace_id == workspace_id]
        if status is not None:
            items = [item for item in items if item.status == status]
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return items[offset:offset + limit], len(items)

    async def get(self, *, workspace_id, saved_report_id):
        item = self.reports.get(saved_report_id)
        return item if item is not None and item.workspace_id == workspace_id else None

    async def update(self, *, workspace_id, saved_report_id, expected_version, changes):
        item = self.reports.get(saved_report_id)
        if item is None or item.workspace_id != workspace_id:
            raise SavedReportNotFoundError(str(saved_report_id))
        if item.version != expected_version:
            raise SavedReportVersionConflictError(expected=expected_version, actual=item.version)
        merged = item.model_dump()
        merged.update(changes)
        merged["version"] = item.version + 1
        merged["updated_at"] = datetime.now(UTC)
        updated = SavedReportDefinition.model_validate(merged)
        self.reports[saved_report_id] = updated
        return updated

    async def create_execution(self, *, workspace_id, saved_report_id, run_id, mode, resolved_period, formats,
                                scheduled_report_id=None, retry_count=0):
        report = self.reports.get(saved_report_id)
        if report is None or report.workspace_id != workspace_id:
            raise SavedReportNotFoundError(str(saved_report_id))
        execution = SavedReportExecution(
            id=uuid4(), saved_report_id=saved_report_id, run_id=run_id, mode=mode, status="running",
            resolved_period_start=resolved_period[0] if resolved_period else None,
            resolved_period_end=resolved_period[1] if resolved_period else None,
            formats=formats, error=None, created_at=datetime.now(UTC), completed_at=None,
        )
        self.executions[run_id] = execution
        return execution

    async def finish_execution(self, *, workspace_id, run_id, status, error, error_category=None,
                                usage_metadata=None, artifact_ids=None):
        existing = self.executions.get(run_id)
        if existing is None:
            return
        report = self.reports.get(existing.saved_report_id)
        if report is None or report.workspace_id != workspace_id:
            return
        self.executions[run_id] = existing.model_copy(
            update={"status": status, "error": error, "completed_at": datetime.now(UTC)}
        )

    async def list_executions(self, *, workspace_id, saved_report_id, limit, offset):
        report = self.reports.get(saved_report_id)
        if report is None or report.workspace_id != workspace_id:
            return None
        items = [item for item in self.executions.values() if item.saved_report_id == saved_report_id]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return items[offset:offset + limit], len(items)


def _create_body(**overrides) -> dict[str, Any]:
    body = {
        "name": "Weekly Revenue",
        "template_id": "analysis_summary",
        "metric_requests": [{"metric": "revenue"}, {"metric": "orders"}],
        "default_period": {"kind": "last_n_days", "days": 7},
        "narrative_policy": "exclude",
    }
    body.update(overrides)
    return body


def _client(
    tmp_path, *, store: "FakeSavedReportStore | None" = None, workspace_id: UUID = WORKSPACE_ID,
) -> TestClient:
    store = store if store is not None else FakeSavedReportStore()
    templates = ReportTemplateRegistry()
    workspace = Workspace(tmp_path)
    artifacts = WorkspaceArtifactStore(workspace, max_artifact_bytes=10_485_760)
    service = SavedReportExecutionService(
        templates=templates, reruns=_FakeRerunService(), workspace=workspace, artifacts=artifacts,
    )
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides = {
        get_saved_report_store: lambda: store,
        get_report_template_registry: lambda: templates,
        get_saved_report_execution_service: lambda: service,
        get_artifact_store: lambda: artifacts,
    }
    override_tenant_context(application, workspace_id=workspace_id)
    return TestClient(application)


class _FakeRerunService:
    """Cheap stand-in so an API test never touches the analytics database."""

    async def run_all(self, *, run_id: str, requests):
        from app.analytics.presentation.charts import ChartSpec, KPIItem
        from app.contracts.answers import AnswerSource
        from app.orchestration.reruns import RerunOutcome

        outcomes = []
        for index, parameters in enumerate(requests, start=1):
            query_id = f"rerun_{index:03d}"
            chart = ChartSpec(id=f"{query_id}-kpi", type="kpi", title=parameters.metric,
                              source_query_ids=[query_id],
                              kpis=[KPIItem(label=parameters.metric, value="1", raw_value=1,
                                           source_column=parameters.metric, source_query_id=query_id)])
            source = AnswerSource(id=query_id, kind="metric_rerun", run_id=run_id, label=parameters.metric,
                                  metric=parameters.metric)
            outcomes.append(RerunOutcome(result=None, source=source, chart=chart))  # type: ignore[arg-type]
        return outcomes


def test_create_returns_the_full_definition_with_a_pinned_template_version(tmp_path) -> None:
    with _client(tmp_path) as client:
        response = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved", json=_create_body())

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Weekly Revenue"
    assert body["template_version"] == ReportTemplateRegistry().get("analysis_summary").version
    assert body["version"] == 1
    assert body["status"] == "active"
    assert body["workspace_id"] == str(WORKSPACE_ID)


def test_create_rejects_an_unknown_template(tmp_path) -> None:
    with _client(tmp_path) as client:
        response = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved", json=_create_body(template_id="not_a_template"))

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "unknown_template"


def test_create_rejects_include_original_without_a_seed(tmp_path) -> None:
    with _client(tmp_path) as client:
        response = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved", json=_create_body(narrative_policy="include_original"),
        )

    assert response.status_code == 422


def test_create_rejects_a_client_supplied_figure(tmp_path) -> None:
    with _client(tmp_path) as client:
        response = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved", json=_create_body(revenue=163))

    assert response.status_code == 422


def test_list_and_get_round_trip(tmp_path) -> None:
    with _client(tmp_path) as client:
        created = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved", json=_create_body()).json()

        listed = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved").json()
        fetched = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved/{created['id']}").json()

    assert listed["total"] == 1
    assert listed["items"][0]["id"] == created["id"]
    assert fetched["metric_requests"] == created["metric_requests"]


def test_get_is_404_for_an_unknown_id(tmp_path) -> None:
    with _client(tmp_path) as client:
        response = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "unknown_saved_report"


def test_get_is_404_across_workspaces(tmp_path) -> None:
    shared_store = FakeSavedReportStore()
    other_workspace_id = uuid4()
    with (
        _client(tmp_path, store=shared_store, workspace_id=WORKSPACE_ID) as client_a,
        _client(tmp_path, store=shared_store, workspace_id=other_workspace_id) as client_b,
    ):
        created = client_a.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved", json=_create_body()).json()

        response = client_b.get(f"/api/v1/workspaces/{other_workspace_id}/reports/saved/{created['id']}")

    assert response.status_code == 404


def test_patch_applies_a_partial_edit_and_bumps_version(tmp_path) -> None:
    with _client(tmp_path) as client:
        created = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved", json=_create_body()).json()

        response = client.patch(
            f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved/{created['id']}",
            json={"expected_version": 1, "name": "Renamed Report"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Renamed Report"
    assert body["version"] == 2
    assert body["template_id"] == created["template_id"]


def test_patch_with_a_stale_version_is_a_409(tmp_path) -> None:
    with _client(tmp_path) as client:
        created = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved", json=_create_body()).json()
        client.patch(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved/{created['id']}", json={"expected_version": 1, "name": "First"})

        response = client.patch(
            f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved/{created['id']}", json={"expected_version": 1, "name": "Conflict"},
        )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "version_conflict"


def test_patch_cannot_supply_a_figure(tmp_path) -> None:
    with _client(tmp_path) as client:
        created = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved", json=_create_body()).json()

        response = client.patch(
            f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved/{created['id']}", json={"expected_version": 1, "revenue": 163},
        )

    assert response.status_code == 422


def test_archive_sets_status_and_is_excluded_from_active_listing(tmp_path) -> None:
    with _client(tmp_path) as client:
        created = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved", json=_create_body()).json()

        archived = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved/{created['id']}/archive", json={"expected_version": 1},
        ).json()
        active_list = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved", params={"status": "active"}).json()

    assert archived["status"] == "archived"
    assert active_list["total"] == 0


def test_resolved_parameters_does_not_execute_anything(tmp_path) -> None:
    with _client(tmp_path) as client:
        created = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved",
            json=_create_body(default_period={"kind": "fixed", "start": "2026-01-01", "end": "2026-01-08"}),
        ).json()

        response = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved/{created['id']}/resolved-parameters")

    assert response.status_code == 200
    body = response.json()
    assert body["resolved_period_start"] == "2026-01-01"
    assert body["resolved_period_end"] == "2026-01-08"
    assert body["template_version_matches_pin"] is True
    assert [item["metric"] for item in body["metric_requests"]] == ["revenue", "orders"]


def test_execute_preview_returns_a_report_and_persists_no_document(tmp_path) -> None:
    with _client(tmp_path) as client:
        created = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved", json=_create_body()).json()

        response = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved/{created['id']}/execute", json={"mode": "preview"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "preview"
    assert body["status"] == "completed"
    assert body["documents"] == []
    assert body["preview"] is not None


def test_execute_publish_returns_a_downloadable_document(tmp_path) -> None:
    with _client(tmp_path) as client:
        created = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved", json=_create_body()).json()

        response = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved/{created['id']}/execute",
            json={"mode": "publish", "formats": ["pdf"]},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "publish"
    assert len(body["documents"]) == 1
    assert body["documents"][0]["media_type"] == "application/pdf"
    assert body["preview"] is None


def test_two_executions_of_the_same_saved_report_mint_different_run_ids(tmp_path) -> None:
    with _client(tmp_path) as client:
        created = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved", json=_create_body()).json()

        first = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved/{created['id']}/execute", json={"mode": "preview"}).json()
        second = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved/{created['id']}/execute", json={"mode": "preview"}).json()

    assert first["run_id"] != second["run_id"]


def test_require_new_investigation_refuses_execution_without_a_model_call(tmp_path) -> None:
    with _client(tmp_path) as client:
        created = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved", json=_create_body(narrative_policy="require_new_investigation"),
        ).json()

        response = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved/{created['id']}/execute", json={"mode": "preview"})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "requires_new_investigation"


def test_executions_are_listed_with_their_artifacts(tmp_path) -> None:
    with _client(tmp_path) as client:
        created = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved", json=_create_body()).json()
        client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved/{created['id']}/execute", json={"mode": "preview"})
        client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved/{created['id']}/execute", json={"mode": "publish", "formats": ["pdf"]},
        )

        response = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved/{created['id']}/executions")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    modes = {item["mode"]: item for item in body["items"]}
    assert modes["preview"]["artifacts"] == []
    assert len(modes["publish"]["artifacts"]) == 1
    assert all(item["status"] == "completed" for item in body["items"])


def test_executions_are_404_for_an_unknown_saved_report(tmp_path) -> None:
    with _client(tmp_path) as client:
        response = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/reports/saved/{uuid4()}/executions")

    assert response.status_code == 404
