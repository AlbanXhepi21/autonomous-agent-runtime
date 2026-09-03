"""Publishing a completed run as a document, without another agent turn."""

import asyncio
from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.analytics.presentation.templates import ReportTemplateRegistry
from app.api.routes.analytics import router
from app.composition import get_report_publisher
from app.orchestration.publishing import ReportPublisher
from tests.support import BACKEND_ROOT, override_tenant_context  # noqa: F401  (keeps path helpers importable)

WORKSPACE_ID = uuid4()

CHART = {
    "id": "chart-1", "type": "bar", "title": "Revenue by category", "x_field": "category",
    "y_fields": ["revenue"], "series": [], "kpis": [],
    "data": [{"category": "Electronics", "revenue": 163}, {"category": "Fashion", "revenue": 63}],
    "source_query_ids": ["query_003"], "formatting": {"show_legend": True},
}
SOURCE = {
    "id": "query_003", "kind": "database_query", "run_id": "run-1", "label": "Revenue by category",
    "referenced_tables": ["orders"], "row_count": 2, "truncated": False, "executed_at": None,
}


async def _value(value: object) -> object:
    return value


def _store(status: str = "completed", **overrides):
    overrides.setdefault("answer_caveats", None)
    run = SimpleNamespace(
        id="run-1", status=status, chart_specs=[CHART], answer_sources=[SOURCE],
        created_at=datetime.now(UTC), **overrides,
    )
    return SimpleNamespace(
        get_run=lambda *, workspace_id, run_id: _value(run),
        get_assistant_message_for_run=lambda *, workspace_id, run_id: _value(
            SimpleNamespace(content="## Finding\nRevenue grew 18%.\n\n- Electronics led.")
        ),
    )


def _client(tmp_path, store) -> TestClient:
    from app.artifacts.store import WorkspaceArtifactStore
    from app.environment.workspace import Workspace

    workspace = Workspace(tmp_path)
    publisher = ReportPublisher(
        ReportTemplateRegistry(), store,
        WorkspaceArtifactStore(workspace, max_artifact_bytes=10_485_760), workspace,
    )
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides = {get_report_publisher: lambda: publisher}
    override_tenant_context(application, workspace_id=WORKSPACE_ID)
    return TestClient(application)


def test_available_templates_describe_their_sections(tmp_path) -> None:
    with _client(tmp_path, _store()) as client:
        body = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/report-templates").json()

    names = [item["name"] for item in body["items"]]
    assert "monthly_business_review" in names
    monthly = next(item for item in body["items"] if item["name"] == "monthly_business_review")
    assert monthly["period_granularity"] == "month"
    assert "Executive Summary" in monthly["sections"]


def test_a_completed_run_publishes_both_formats(tmp_path) -> None:
    with _client(tmp_path, _store()) as client:
        response = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/run-1/reports",
            json={"template": "monthly_business_review", "formats": ["pdf", "docx"],
                  "period": "August 2026"},
        )

    assert response.status_code == 201
    documents = response.json()["documents"]
    assert [item["media_type"] for item in documents] == [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    # A document carrying a rendered chart is not a few kilobytes; this also
    # guards the artifact size limit that previously rejected them.
    assert all(item["size"] > 20_000 for item in documents)


def test_each_published_document_is_recorded_with_what_wrote_it(tmp_path) -> None:
    """The record has to say which template and format produced these bytes."""

    from app.artifacts.contracts import ArtifactStatus
    from app.artifacts.files import digest_of
    from app.artifacts.store import WorkspaceArtifactStore
    from app.environment.workspace import Workspace

    workspace = Workspace(tmp_path)
    store = WorkspaceArtifactStore(workspace, max_artifact_bytes=10_485_760)
    publisher = ReportPublisher(ReportTemplateRegistry(), _store(), store, workspace)

    published = asyncio.run(publisher.publish(
        workspace_id=WORKSPACE_ID, run_id="run-1", template_name="monthly_business_review", formats=["pdf", "docx"],
    ))

    assert [item.output_format for item in published] == ["pdf", "docx"]
    for artifact in published:
        assert artifact.status is ArtifactStatus.READY
        assert artifact.template_id == "monthly_business_review"
        # Whatever the template currently declares — bumping a shape must not
        # need this test edited, only the artifact to keep recording it.
        assert artifact.template_version == ReportTemplateRegistry().get(
            "monthly_business_review"
        ).version
        assert artifact.artifact_type == "report_document"
        # Nothing machine-specific reaches the record.
        assert artifact.relative_path == f"artifacts/run-1/{artifact.id}/{artifact.name}"
        assert str(tmp_path) not in artifact.relative_path
        path = asyncio.run(store.path_for(workspace_id=WORKSPACE_ID, artifact_id=artifact.id))
        assert path is not None
        written = digest_of(path)
        assert (artifact.size, artifact.sha256) == (written.size, written.sha256)


def test_an_unfinished_run_is_not_publishable(tmp_path) -> None:
    with _client(tmp_path, _store(status="running")) as client:
        response = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/run-1/reports",
            json={"template": "monthly_business_review", "formats": ["pdf"]},
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "report_not_published"


def test_an_unknown_template_is_refused(tmp_path) -> None:
    with _client(tmp_path, _store()) as client:
        response = client.post(
            f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/run-1/reports",
            json={"template": "not_a_template", "formats": ["pdf"]},
        )

    assert response.status_code == 400


CAVEATS = ["Refund timing may differ from order timing.", "August 2026 is a partial month."]


def _legacy_store():
    """A run persisted before the caveats column existed, so the field is absent."""

    run = SimpleNamespace(id="run-1", status="completed", chart_specs=[CHART],
                          answer_sources=[SOURCE], created_at=datetime.now(UTC))
    assert not hasattr(run, "answer_caveats")
    return SimpleNamespace(
        get_run=lambda *, workspace_id, run_id: _value(run),
        get_assistant_message_for_run=lambda *, workspace_id, run_id: _value(
            SimpleNamespace(content="## Finding\nRevenue grew 18%.")
        ),
    )


def _publish(tmp_path, store, formats=("pdf", "docx")):
    from app.artifacts.store import WorkspaceArtifactStore
    from app.environment.workspace import Workspace

    workspace = Workspace(tmp_path)
    artifacts = WorkspaceArtifactStore(workspace, max_artifact_bytes=10_485_760)
    publisher = ReportPublisher(ReportTemplateRegistry(), store, artifacts, workspace)
    published = asyncio.run(publisher.publish(
        workspace_id=WORKSPACE_ID, run_id="run-1", template_name="monthly_business_review", formats=list(formats),
    ))
    return published, artifacts


def _text(artifact, artifacts):
    from docx import Document
    from pypdf import PdfReader

    path = asyncio.run(artifacts.path_for(workspace_id=WORKSPACE_ID, artifact_id=artifact.id))
    if artifact.output_format == "pdf":
        raw = "\n".join(page.extract_text() for page in PdfReader(str(path)).pages)
    else:
        raw = "\n".join(paragraph.text for paragraph in Document(str(path)).paragraphs)
    return " ".join(raw.split())


def test_stored_caveats_reach_both_published_formats(tmp_path) -> None:
    """The model wrote these when it finished; publishing only prints them."""

    published, artifacts = _publish(tmp_path, _store(answer_caveats=CAVEATS))

    for artifact in published:
        text = _text(artifact, artifacts)
        assert all(caveat in text for caveat in CAVEATS), artifact.output_format
        assert artifact.metadata["caveat_count"] == len(CAVEATS)


def test_a_run_recorded_before_caveats_existed_still_publishes(tmp_path) -> None:
    """Backward compatibility: an older row has no caveats field at all."""

    published, artifacts = _publish(tmp_path, _legacy_store())

    for artifact in published:
        text = _text(artifact, artifacts)
        assert "This analysis stated no limitations." in text
        assert "Query citations confirm that the referenced query executed." in text
        assert artifact.metadata["caveat_count"] == 0


def test_stored_caveats_are_re_normalized_on_the_way_out(tmp_path) -> None:
    """A row written by an older or looser writer cannot publish a bad limitation."""

    stored = ["  Sample of 12 orders.  ", "Sample of 12 orders.", "", "x" * 501]

    published, artifacts = _publish(tmp_path, _store(answer_caveats=stored), formats=("docx",))

    text = _text(published[0], artifacts)
    assert text.count("Sample of 12 orders.") == 1
    assert "x" * 501 not in text
    assert published[0].metadata["caveat_count"] == 1


def test_publishing_cannot_reach_a_model_at_all(tmp_path) -> None:
    """Publishing is assembly, and the import graph is what keeps it that way.

    Asserting that no call was made would pass trivially, since the publisher
    never had a client to call. This asserts the stronger property: nothing the
    publisher imports, transitively, can reach the provider package — so a model
    call cannot be added here without the boundary failing first.
    """

    import ast
    from collections import deque

    from tests.support import BACKEND_ROOT

    def module_path(name: str):
        base = BACKEND_ROOT / name.replace(".", "/")
        for candidate in (base.with_suffix(".py"), base / "__init__.py"):
            if candidate.is_file():
                return candidate
        return None

    seen, queue = set(), deque(["app.orchestration.publishing"])
    while queue:
        name = queue.popleft()
        if name in seen or (path := module_path(name)) is None:
            continue
        seen.add(name)
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app."):
                queue.append(node.module)
            elif isinstance(node, ast.Import):
                queue.extend(a.name for a in node.names if a.name.startswith("app."))

    assert "app.orchestration.publishing" in seen
    assert not [name for name in seen if name.startswith("app.llm")], (
        "publishing reaches the LLM provider package"
    )

    # And the documents it writes still carry what the run stored.
    published, artifacts = _publish(tmp_path, _store(answer_caveats=CAVEATS), formats=("docx",))
    assert all(caveat in _text(published[0], artifacts) for caveat in CAVEATS)


# ------------------------------------------------------- parameterized reruns


class FakeRunner:
    """A metric runner that records what it was asked, without a database."""

    def __init__(self, rows=None):
        self.requests = []
        self._rows = rows if rows is not None else [{"revenue": "163.00", "order_count": 12}]

    async def run(self, parameters):
        from app.analytics.semantics.execution import MetricResult

        self.requests.append(parameters)
        return MetricResult(
            metric=parameters.metric, metric_version="v1", display_name="Revenue",
            format="currency", unit="USD", parameters=parameters,
            columns=tuple(self._rows[0]), dimension_columns=tuple(parameters.dimensions),
            value_columns=("revenue", "order_count"),
            rows=tuple(self._rows), tables_consulted=("orders",), row_count=len(self._rows),
            truncated=False, executed_at=datetime.now(UTC), execution_ms=7,
            sql_fingerprint="fingerprint01",
        )


def _rerun_publisher(tmp_path, runner=None):
    from app.artifacts.store import WorkspaceArtifactStore
    from app.environment.workspace import Workspace
    from app.orchestration.reruns import ReportRerunService

    workspace = Workspace(tmp_path)
    artifacts = WorkspaceArtifactStore(workspace, max_artifact_bytes=10_485_760)
    publisher = ReportPublisher(
        ReportTemplateRegistry(), _store(answer_caveats=CAVEATS), artifacts, workspace,
        ReportRerunService(runner or FakeRunner()),
    )
    return publisher, artifacts


def _parameters(**overrides):
    from app.analytics.semantics.parameters import MetricParameters, ReportPeriod

    return MetricParameters(
        metric=overrides.pop("metric", "revenue"),
        period=overrides.pop("period", ReportPeriod(start=date(2026, 1, 1), end=date(2026, 4, 1))),
        **overrides,
    )


def test_a_rerun_replaces_the_figures_and_cites_its_own_evidence(tmp_path) -> None:
    publisher, artifacts = _rerun_publisher(tmp_path)

    published = asyncio.run(publisher.publish(
        workspace_id=WORKSPACE_ID, run_id="run-1", template_name="monthly_business_review", formats=["docx"],
        period="March 2026", metrics=[_parameters()],
    ))

    text = _text(published[0], artifacts)
    # The recomputed evidence, not the agent run's query_003.
    assert "rerun_001" in text
    assert "query_003" not in text
    assert published[0].metadata["recomputed_metrics"] == ["revenue"]
    assert published[0].metadata["narrative_status"] == "excluded_from_refreshed_report"


def test_a_rerun_drops_the_original_prose_by_default(tmp_path) -> None:
    """The safe default: prose that never saw this data is not printed above it."""

    publisher, artifacts = _rerun_publisher(tmp_path)

    published = asyncio.run(publisher.publish(
        workspace_id=WORKSPACE_ID, run_id="run-1", template_name="monthly_business_review", formats=["docx"],
        period="March 2026", metrics=[_parameters()],
    ))

    text = _text(published[0], artifacts)
    assert "Revenue grew 18%." not in text
    assert "recomputed for a different period" in text


def test_a_rerun_may_keep_the_prose_under_a_visible_warning(tmp_path) -> None:
    publisher, artifacts = _rerun_publisher(tmp_path)

    published = asyncio.run(publisher.publish(
        workspace_id=WORKSPACE_ID, run_id="run-1", template_name="monthly_business_review", formats=["docx"],
        period="March 2026", metrics=[_parameters()],
        narrative="pinned_to_original_period",
    ))

    text = _text(published[0], artifacts)
    assert "Revenue grew 18%." in text
    assert "has been kept unchanged" in text
    assert "March 2026" in text


def test_the_printed_period_comes_from_the_request_not_the_caller(tmp_path) -> None:
    """A typed label must not be able to disagree with the data behind it."""

    publisher, artifacts = _rerun_publisher(tmp_path)

    published = asyncio.run(publisher.publish(
        workspace_id=WORKSPACE_ID, run_id="run-1", template_name="monthly_business_review", formats=["docx"],
        period="Whatever the caller typed", metrics=[_parameters()],
    ))

    text = _text(published[0], artifacts)
    assert "2026-01-01 to 2026-03-31" in text


def test_the_rerun_service_receives_exactly_what_was_asked(tmp_path) -> None:
    from app.analytics.semantics.parameters import MetricFilter

    runner = FakeRunner()
    publisher, _ = _rerun_publisher(tmp_path, runner)

    asyncio.run(publisher.publish(
        workspace_id=WORKSPACE_ID, run_id="run-1", template_name="monthly_business_review", formats=["docx"],
        metrics=[_parameters(dimensions=["period"],
                             filters=[MetricFilter(field="country", value="Germany")])],
    ))

    assert len(runner.requests) == 1
    request = runner.requests[0]
    assert request.metric == "revenue"
    assert request.dimensions == ["period"]
    assert request.filters[0].value == "Germany"


def test_publishing_a_rerun_calls_no_model(tmp_path) -> None:
    """Recomputing is compilation and execution. Nothing here asks a model."""

    reachable = _reachable_modules("app.orchestration.reruns")

    assert not [name for name in reachable if name.startswith("app.llm")]
    assert "app.analytics.semantics.execution" in reachable

    publisher, artifacts = _rerun_publisher(tmp_path)
    published = asyncio.run(publisher.publish(
        workspace_id=WORKSPACE_ID, run_id="run-1", template_name="monthly_business_review", formats=["docx"],
        metrics=[_parameters()],
    ))
    assert "rerun_001" in _text(published[0], artifacts)


def _reachable_modules(start: str) -> set[str]:
    import ast
    from collections import deque

    from tests.support import BACKEND_ROOT

    def path_of(name: str):
        base = BACKEND_ROOT / name.replace(".", "/")
        for candidate in (base.with_suffix(".py"), base / "__init__.py"):
            if candidate.is_file():
                return candidate
        return None

    seen, queue = set(), deque([start])
    while queue:
        name = queue.popleft()
        path = path_of(name)
        if name in seen or path is None:
            continue
        seen.add(name)
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app."):
                queue.append(node.module)
            elif isinstance(node, ast.Import):
                queue.extend(a.name for a in node.names if a.name.startswith("app."))
    return seen


def test_a_report_may_not_recompute_an_unbounded_number_of_sections(tmp_path) -> None:
    from app.orchestration.publishing import ReportPublishingError

    publisher, _ = _rerun_publisher(tmp_path)

    with pytest.raises(ReportPublishingError, match="at most"):
        asyncio.run(publisher.publish(
            workspace_id=WORKSPACE_ID, run_id="run-1", template_name="monthly_business_review", formats=["docx"],
            metrics=[_parameters() for _ in range(9)],
        ))


def test_a_server_without_the_rerun_service_refuses_rather_than_ignoring(tmp_path) -> None:
    """Silently publishing the original figures would be the wrong answer."""

    from app.artifacts.store import WorkspaceArtifactStore
    from app.environment.workspace import Workspace
    from app.orchestration.publishing import ReportPublishingError

    workspace = Workspace(tmp_path)
    publisher = ReportPublisher(
        ReportTemplateRegistry(), _store(), 
        WorkspaceArtifactStore(workspace, max_artifact_bytes=10_485_760), workspace,
    )

    with pytest.raises(ReportPublishingError, match="not configured"):
        asyncio.run(publisher.publish(
            workspace_id=WORKSPACE_ID, run_id="run-1", template_name="monthly_business_review", formats=["docx"],
            metrics=[_parameters()],
        ))
