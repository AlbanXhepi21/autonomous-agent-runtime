"""Deterministic report preview, template suitability, and publish consistency."""

import ast
from collections import deque
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.analytics.presentation.templates import ReportTemplateRegistry
from app.api.routes.analytics import router
from app.composition import get_report_publisher
from app.orchestration.publishing import ReportPublisher
from tests.support import BACKEND_ROOT, override_tenant_context

WORKSPACE_ID = uuid4()


def _kpi(chart_id: str, items: int, query_id: str) -> dict:
    return {
        "id": chart_id, "type": "kpi", "title": "Headline metrics", "source_query_ids": [query_id],
        "kpis": [{"label": f"Metric {i}", "value": str(i)} for i in range(items)],
    }


def _bar(chart_id: str, query_id: str, title: str = "Failures by method") -> dict:
    return {
        "id": chart_id, "type": "bar", "title": title, "x_field": "method", "y_fields": ["count"],
        "data": [{"method": "card", "count": 12}, {"method": "wallet", "count": 4}],
        "source_query_ids": [query_id],
    }


def _line(chart_id: str, query_id: str, title: str = "Monthly trend") -> dict:
    return {
        "id": chart_id, "type": "line", "title": title, "x_field": "month", "y_fields": ["count"],
        "data": [{"month": "2026-01", "count": 3}, {"month": "2026-02", "count": 5}],
        "source_query_ids": [query_id],
    }


def _table(chart_id: str, query_id: str, title: str = "Supporting rows") -> dict:
    return {
        "id": chart_id, "type": "table", "title": title,
        "data": [{"method": "card", "reason": "insufficient_funds", "count": 12}],
        "source_query_ids": [query_id],
    }


def _source(query_id: str, label: str) -> dict:
    return {
        "id": query_id, "kind": "database_query", "run_id": "run-1", "label": label,
        "referenced_tables": ["payments"], "row_count": 2, "truncated": False, "executed_at": None,
    }


SUFFICIENT_CHARTS = [
    _kpi("c-kpi", 4, "query_001"),
    _line("c-trend", "query_002"),
    _bar("c-breakdown", "query_003"),
    _table("c-table", "query_004"),
]
SUFFICIENT_SOURCES = [_source(f"query_{i:03d}", f"Query {i}") for i in range(1, 5)]

ONE_CHART = [_bar("c-only", "query_001")]
ONE_SOURCE = [_source("query_001", "Query 1")]


async def _value(value: object) -> object:
    return value


def _store(chart_specs: list[dict], answer_sources: list[dict], *, status: str = "completed"):
    run = SimpleNamespace(
        id="run-1", status=status, chart_specs=chart_specs, answer_sources=answer_sources,
        answer_caveats=None, created_at=datetime.now(UTC),
    )
    return SimpleNamespace(
        get_run=lambda *, workspace_id, run_id: _value(run),
        get_assistant_message_for_run=lambda *, workspace_id, run_id: _value(SimpleNamespace(content="Payment failures rose.")),
    )


def _publisher(tmp_path, store) -> ReportPublisher:
    from app.artifacts.store import WorkspaceArtifactStore
    from app.environment.workspace import Workspace

    workspace = Workspace(tmp_path)
    return ReportPublisher(
        ReportTemplateRegistry(), store, WorkspaceArtifactStore(workspace, max_artifact_bytes=10_485_760), workspace,
    )


def _client(tmp_path, store) -> TestClient:
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides = {get_report_publisher: lambda: _publisher(tmp_path, store)}
    override_tenant_context(application, workspace_id=WORKSPACE_ID)
    return TestClient(application)


# ------------------------------------------------------------ scenario tests


def test_executive_dashboard_with_sufficient_content_is_publishable(tmp_path) -> None:
    with _client(tmp_path, _store(SUFFICIENT_CHARTS, SUFFICIENT_SOURCES)) as client:
        response = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/run-1/report-preview", json={"template": "executive_dashboard"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["suitability"]["can_publish"] is True
    assert body["suitability"]["missing_required_slots"] == []
    assert body["missing_required_content"] == []
    assert body["estimated_page_count"] >= 1
    assert body["template_name"] == "executive_dashboard"


def test_executive_dashboard_with_only_one_chart_reports_missing_content(tmp_path) -> None:
    with _client(tmp_path, _store(ONE_CHART, ONE_SOURCE)) as client:
        response = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/run-1/report-preview", json={"template": "executive_dashboard"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["suitability"]["can_publish"] is False
    assert "headline_metrics" in body["suitability"]["missing_required_slots"]
    assert body["missing_required_content"]
    assert any("headline_metrics" in message for message in body["missing_required_content"])


def test_analysis_summary_recommended_for_a_small_run(tmp_path) -> None:
    with _client(tmp_path, _store(ONE_CHART, ONE_SOURCE)) as client:
        response = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/run-1/report-suitability")

    assert response.status_code == 200
    body = response.json()
    assert body["recommended_template"] == "analysis_summary"
    summary = next(item for item in body["items"] if item["template_name"] == "analysis_summary")
    assert summary["can_publish"] is True
    assert summary["completion_percentage"] == 100.0
    dashboard = next(item for item in body["items"] if item["template_name"] == "executive_dashboard")
    assert dashboard["can_publish"] is False


def test_no_display_is_assigned_to_more_than_one_slot(tmp_path) -> None:
    with _client(tmp_path, _store(SUFFICIENT_CHARTS, SUFFICIENT_SOURCES)) as client:
        response = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/run-1/report-preview", json={"template": "monthly_business_review"}
        )

    body = response.json()
    assigned = [chart_id for slot in body["assignment"]["slots"] for chart_id in slot["assigned_chart_ids"]]
    assert len(assigned) == len(set(assigned))


def test_preview_assignment_is_deterministic_across_repeated_calls(tmp_path) -> None:
    with _client(tmp_path, _store(SUFFICIENT_CHARTS, SUFFICIENT_SOURCES)) as client:
        first = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/run-1/report-preview", json={"template": "monthly_business_review"}
        ).json()
        second = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/run-1/report-preview", json={"template": "monthly_business_review"}
        ).json()

    assert first["assignment"] == second["assignment"]
    assert first["suitability"] == second["suitability"]


def test_missing_required_slots_are_reported_when_a_run_has_no_displays(tmp_path) -> None:
    with _client(tmp_path, _store([], [])) as client:
        response = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/run-1/report-preview", json={"template": "quarterly_review"}
        )

    body = response.json()
    assert body["suitability"]["can_publish"] is False
    assert set(body["suitability"]["missing_required_slots"]) == {
        "headline_metrics", "key_breakdowns", "supporting_tables",
    }


def test_unknown_evidence_is_excluded_from_the_preview(tmp_path) -> None:
    fabricated = _bar("c-fake", "query_999", title="Fabricated breakdown")
    charts = [*SUFFICIENT_CHARTS, fabricated]
    with _client(tmp_path, _store(charts, SUFFICIENT_SOURCES)) as client:
        response = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/run-1/report-preview", json={"template": "monthly_business_review"}
        )

    body = response.json()
    assert "c-fake" in body["assignment"]["unresolved_evidence_chart_ids"]
    assigned = [chart_id for slot in body["assignment"]["slots"] for chart_id in slot["assigned_chart_ids"]]
    assert "c-fake" not in assigned


def test_a_run_that_cannot_be_published_cannot_be_previewed_either(tmp_path) -> None:
    with _client(tmp_path, _store(SUFFICIENT_CHARTS, SUFFICIENT_SOURCES, status="running")) as client:
        response = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/run-1/report-preview", json={"template": "monthly_business_review"}
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "report_not_previewable"


# ------------------------------------------------------------ no-model boundary


def test_preview_never_reaches_the_llm_package() -> None:
    """Mirrors `test_publishing_never_reaches_a_model` for the new preview path."""

    reachable: set[str] = set()
    queue = deque([
        "app.orchestration.publishing", "app.analytics.presentation.preview",
        "app.analytics.presentation.assignment", "app.analytics.presentation.suitability",
    ])
    while queue:
        name = queue.popleft()
        if name in reachable:
            continue
        reachable.add(name)
        path = BACKEND_ROOT / "app" / (name.removeprefix("app.").replace(".", "/") + ".py")
        if not path.is_file():
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app."):
                queue.append(node.module)
            elif isinstance(node, ast.Import):
                queue.extend(alias.name for alias in node.names if alias.name.startswith("app."))

    assert not [name for name in reachable if name.startswith("app.llm")]


def test_the_preview_request_carries_no_figures() -> None:
    """Mirrors `test_the_publish_request_carries_no_figures` for the preview request."""

    from app.api.schemas.analytics import ReportPreviewRequest

    fields = ReportPreviewRequest.model_fields
    assert set(fields) == {"template", "period", "title", "metrics", "narrative"}
    for name in ("template", "period", "title"):
        annotation = str(fields[name].annotation)
        assert "int" not in annotation and "float" not in annotation

    with pytest.raises(ValueError):
        ReportPreviewRequest(template="monthly_business_review", revenue=163)


# ------------------------------------------------------------ publish consistency


@pytest.mark.asyncio
async def test_publishing_uses_exactly_the_previewed_assignment(tmp_path) -> None:
    store = _store(SUFFICIENT_CHARTS, SUFFICIENT_SOURCES)
    publisher = _publisher(tmp_path, store)

    preview = await publisher.preview(workspace_id=WORKSPACE_ID, run_id="run-1", template_name="monthly_business_review", period="Jan 2026")
    [artifact] = await publisher.publish(
        workspace_id=WORKSPACE_ID, run_id="run-1", template_name="monthly_business_review", formats=["pdf"], period="Jan 2026",
    )

    previewed_chart_ids = [block.chart_id for block in preview.report.blocks_of("chart")]
    assert artifact.metadata["chart_count"] == len(previewed_chart_ids)
    assert artifact.metadata["source_query_ids"] == preview.report.cited_query_ids
    assert artifact.metadata["template"] == preview.template_name

    # Publishing the same request again compiles through the same pure path,
    # so a second preview of it must report the identical assignment.
    second_preview = await publisher.preview(workspace_id=WORKSPACE_ID, run_id="run-1", template_name="monthly_business_review", period="Jan 2026")
    assert second_preview.assignment.model_dump() == preview.assignment.model_dump()
