"""Report-publish precedence: explicit request > workspace report defaults > system default.

``ReportPreferences`` (``app.tenancy.contracts``) is a workspace's own
presentation defaults -- stored but, before this change, never actually
consulted when a run was published (see ``app.api.routes.analytics``). These
tests exercise the resolution chain end to end through the HTTP routes, plus
the resolved locale/timezone/currency an organization's own settings stamp
into the published artifact's metadata for reproducibility.
"""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.analytics.presentation.templates import ReportTemplateRegistry
from app.api.routes.analytics import router
from app.composition import get_report_publisher, get_tenancy_service
from app.identity.email import FileEmailSender
from app.orchestration.publishing import ReportPublisher
from app.tenancy.service import TenancyService
from app.tenancy.store import (
    InMemoryInvitationStore,
    InMemoryMembershipStore,
    InMemoryReportPreferencesStore,
    InMemoryWorkspaceStore,
)
from tests.support import override_tenant_context

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


def _store() -> SimpleNamespace:
    run = SimpleNamespace(
        id="run-1", status="completed", chart_specs=[CHART], answer_sources=[SOURCE],
        created_at=datetime.now(UTC), answer_caveats=None,
    )
    return SimpleNamespace(
        get_run=lambda *, workspace_id, run_id: _value(run),
        get_assistant_message_for_run=lambda *, workspace_id, run_id: _value(
            SimpleNamespace(content="## Finding\nRevenue grew 18%.")
        ),
    )


def _tenancy_service(tmp_path, *, default_template: str | None = None, default_output_format: str | None = None) -> TenancyService:
    preferences_store = InMemoryReportPreferencesStore()
    service = TenancyService(
        workspaces=InMemoryWorkspaceStore(), memberships=InMemoryMembershipStore(),
        invitations=InMemoryInvitationStore(), email_sender=FileEmailSender(tmp_path / ".dev-mail"),
        invitation_ttl_seconds=604_800, app_base_url="http://localhost:3000",
        report_preferences=preferences_store,
    )
    return service


def _client(
    tmp_path, *, workspace_id, default_template: str | None = None, default_output_format: str | None = None,
    default_timezone: str = "UTC", default_locale: str = "en-US", default_currency: str = "USD",
):
    from app.artifacts.store import WorkspaceArtifactStore
    from app.environment.workspace import Workspace

    workspace = Workspace(tmp_path)
    artifacts = WorkspaceArtifactStore(workspace, max_artifact_bytes=10_485_760)
    publisher = ReportPublisher(ReportTemplateRegistry(), _store(), artifacts, workspace)
    tenancy = _tenancy_service(tmp_path)
    if default_template is not None or default_output_format is not None:
        seeded = asyncio.run(tenancy.get_report_preferences(workspace_id=workspace_id))
        asyncio.run(tenancy.update_report_preferences(
            workspace_id=workspace_id, expected_version=seeded.version,
            changes={"default_template": default_template, "default_output_format": default_output_format},
            actor_user_id=uuid4(),
        ))

    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_report_publisher] = lambda: publisher
    application.dependency_overrides[get_tenancy_service] = lambda: tenancy
    override_tenant_context(
        application, workspace_id=workspace_id, default_timezone=default_timezone,
        default_locale=default_locale, default_currency=default_currency,
    )
    return TestClient(application), tenancy, artifacts


def test_publish_without_a_template_falls_back_to_the_workspace_default(tmp_path) -> None:
    workspace_id = uuid4()
    client, _, _artifacts_unused = _client(
        tmp_path, workspace_id=workspace_id, default_template="monthly_business_review",
        default_output_format="docx",
    )
    with client:
        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/analytics/runs/run-1/reports", json={},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["template"] == "monthly_business_review"
    assert body["documents"][0]["media_type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_an_explicit_template_overrides_the_workspace_default(tmp_path) -> None:
    workspace_id = uuid4()
    client, _, _artifacts_unused = _client(
        tmp_path, workspace_id=workspace_id, default_template="executive_dashboard",
        default_output_format="docx",
    )
    with client:
        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/analytics/runs/run-1/reports",
            json={"template": "monthly_business_review", "formats": ["pdf"]},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["template"] == "monthly_business_review"
    assert body["documents"][0]["media_type"] == "application/pdf"


def test_no_template_and_no_workspace_default_is_rejected(tmp_path) -> None:
    workspace_id = uuid4()
    client, _, _artifacts_unused = _client(tmp_path, workspace_id=workspace_id)
    with client:
        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/analytics/runs/run-1/reports", json={},
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "template_required"


def test_no_workspace_default_format_falls_back_to_pdf(tmp_path) -> None:
    workspace_id = uuid4()
    client, _, _artifacts_unused = _client(tmp_path, workspace_id=workspace_id, default_template="monthly_business_review")
    with client:
        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/analytics/runs/run-1/reports", json={},
        )

    assert response.status_code == 201
    assert response.json()["documents"][0]["media_type"] == "application/pdf"


def test_two_workspaces_resolve_their_own_report_defaults(tmp_path) -> None:
    """Mirrors the acceptance scenario: two organizations owned by the same
    user, each with its own template default -- switching which workspace a
    request targets must never leak the other's configuration."""

    org_a = uuid4()
    org_b = uuid4()
    client_a, _, _artifacts_a = _client(
        tmp_path / "a", workspace_id=org_a, default_template="monthly_business_review",
        default_currency="EUR",
    )
    client_b, _, _artifacts_b = _client(
        tmp_path / "b", workspace_id=org_b, default_template="executive_dashboard",
        default_currency="USD",
    )

    with client_a:
        response_a = client_a.post(f"/api/v1/workspaces/{org_a}/analytics/runs/run-1/reports", json={})
    with client_b:
        response_b = client_b.post(f"/api/v1/workspaces/{org_b}/analytics/runs/run-1/reports", json={})

    assert response_a.json()["template"] == "monthly_business_review"
    assert response_b.json()["template"] == "executive_dashboard"


def test_resolved_locale_timezone_currency_are_stamped_into_the_artifact(tmp_path) -> None:
    from app.artifacts.store import WorkspaceArtifactStore
    from app.environment.workspace import Workspace

    workspace_id = uuid4()
    workspace = Workspace(tmp_path)
    artifacts = WorkspaceArtifactStore(workspace, max_artifact_bytes=10_485_760)
    publisher = ReportPublisher(ReportTemplateRegistry(), _store(), artifacts, workspace)

    published = asyncio.run(publisher.publish(
        workspace_id=workspace_id, run_id="run-1", template_name="monthly_business_review", formats=["pdf"],
        resolved_locale="fr-FR", resolved_timezone="Europe/Paris", resolved_currency="EUR",
    ))

    assert published[0].metadata["resolved_locale"] == "fr-FR"
    assert published[0].metadata["resolved_timezone"] == "Europe/Paris"
    assert published[0].metadata["resolved_currency"] == "EUR"


def test_changing_report_preferences_does_not_alter_an_already_published_artifact(tmp_path) -> None:
    """Section 3/16 of the settings-separation requirement: a preferences
    edit must never rewrite a document that has already been published."""

    workspace_id = uuid4()
    client, tenancy, artifacts = _client(
        tmp_path, workspace_id=workspace_id, default_template="monthly_business_review",
        default_currency="USD",
    )
    with client:
        first = client.post(f"/api/v1/workspaces/{workspace_id}/analytics/runs/run-1/reports", json={})
        assert first.status_code == 201
        original_artifact_id = first.json()["documents"][0]["artifact_id"]

        seeded = asyncio.run(tenancy.get_report_preferences(workspace_id=workspace_id))
        asyncio.run(tenancy.update_report_preferences(
            workspace_id=workspace_id, expected_version=seeded.version,
            changes={"default_template": "executive_dashboard", "default_currency": "EUR"},
            actor_user_id=uuid4(),
        ))

    # The previously published artifact is untouched -- still recorded against
    # the template and currency actually in effect when it was published,
    # regardless of what the workspace's own defaults changed to afterward.
    record = asyncio.run(artifacts.get(workspace_id=workspace_id, artifact_id=original_artifact_id))
    assert record is not None
    assert record.template_id == "monthly_business_review"
    assert record.metadata["resolved_currency"] == "USD"
