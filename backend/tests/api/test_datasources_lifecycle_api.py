"""The administrative connection-lifecycle surface: edit, replace credentials,
enable/disable, soft-delete -- plus the RBAC and cross-tenant behavior around them.

Reuses the in-process fakes from ``test_datasources_api.py`` (same rationale:
the live-connection parts are proven for real in
``tests/integration/test_datasource_onboarding_service.py``); this suite is
only about the API contract for the lifecycle operations added on top of
onboarding.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.datasources import router
from app.composition import get_data_source_onboarding_service, get_data_source_store
from app.tenancy.contracts import Role
from tests.api.test_datasources_api import FakeDataSourceStore, FakeOnboardingService, _create_body
from tests.support import override_tenant_context

WORKSPACE_A = uuid4()
WORKSPACE_B = uuid4()


def _client(store: FakeDataSourceStore, service: FakeOnboardingService, *, workspace_id=WORKSPACE_A, role: Role = Role.OWNER) -> TestClient:
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides = {
        get_data_source_store: lambda: store,
        get_data_source_onboarding_service: lambda: service,
    }
    override_tenant_context(application, workspace_id=workspace_id, role=role)
    return TestClient(application)


def _created(store: FakeDataSourceStore, service: FakeOnboardingService, workspace_id=WORKSPACE_A) -> dict:
    return _client(store, service, workspace_id=workspace_id).post(
        f"/api/v1/workspaces/{workspace_id}/datasources", json=_create_body(),
    ).json()


# -- update configuration -----------------------------------------------------


def test_update_edits_name_and_description_without_touching_credentials() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)

    response = _client(store, service).patch(
        f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}",
        json={"name": "Renamed", "description": "Now with a description"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Renamed"
    assert body["description"] == "Now with a description"
    assert body["host"] == created["host"]
    assert "password" not in body


def test_update_with_a_partial_connection_detail_change_is_rejected() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)

    response = _client(store, service).patch(
        f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}",
        json={"host": "new-host.example.com"},
    )

    assert response.status_code == 422


def test_update_with_a_full_connection_detail_change_resets_status_and_bumps_version() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)
    client = _client(store, service)
    client.post(f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}/test-connection")

    response = client.patch(
        f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}",
        json={
            "host": "new-host.example.com", "port": 5432, "database": "analytics", "username": "ro_user",
            "ssl_mode": "require", "allowed_schemas": ["public"], "statement_timeout_seconds": 15,
            "connection_timeout_seconds": 10, "max_result_rows": 5000, "max_result_bytes": 1000000,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["host"] == "new-host.example.com"
    assert body["status"] == "pending"
    assert body["version"] == 2


def test_update_is_404_across_workspaces() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service, workspace_id=WORKSPACE_A)

    response = _client(store, service, workspace_id=WORKSPACE_B).patch(
        f"/api/v1/workspaces/{WORKSPACE_B}/datasources/{created['id']}", json={"name": "Hijacked"},
    )

    assert response.status_code == 404


def test_analyst_cannot_update_configuration() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)

    response = _client(store, service, role=Role.ANALYST).patch(
        f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}", json={"name": "Nope"},
    )

    assert response.status_code == 403


def test_viewer_cannot_update_configuration() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)

    response = _client(store, service, role=Role.VIEWER).patch(
        f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}", json={"name": "Nope"},
    )

    assert response.status_code == 403


# -- replace credentials -------------------------------------------------------


def test_replace_credentials_never_echoes_the_new_password() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)

    response = _client(store, service).post(
        f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}/replace-credentials",
        json={"password": "new-super-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "password" not in body
    assert "new-super-secret" not in response.text


def test_replace_credentials_resets_status_and_bumps_version() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)
    client = _client(store, service)
    client.post(f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}/test-connection")

    response = client.post(
        f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}/replace-credentials",
        json={"password": "new-super-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["version"] == 2


def test_replace_credentials_updates_the_stored_ciphertext_not_the_visible_shape() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)
    client = _client(store, service)

    client.post(
        f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}/replace-credentials",
        json={"password": "rotated-secret"},
    )

    assert store.passwords[UUID(created["id"])] == "encrypted:rotated-secret"


def test_analyst_cannot_replace_credentials() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)

    response = _client(store, service, role=Role.ANALYST).post(
        f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}/replace-credentials",
        json={"password": "hijacked"},
    )

    assert response.status_code == 403


# -- enable / disable -----------------------------------------------------------


def test_disable_then_enable_round_trips_through_pending() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)
    client = _client(store, service)

    disabled = client.post(f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}/disable")
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"

    enabled = client.post(f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}/enable")
    assert enabled.status_code == 200
    assert enabled.json()["status"] == "pending"


def test_enabling_a_data_source_that_is_not_disabled_is_refused() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)

    response = _client(store, service).post(f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}/enable")

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "not_disabled"


def test_disabling_twice_is_idempotent() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)
    client = _client(store, service)
    client.post(f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}/disable")

    response = client.post(f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}/disable")

    assert response.status_code == 200
    assert response.json()["status"] == "disabled"


def test_viewer_cannot_disable() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)

    response = _client(store, service, role=Role.VIEWER).post(
        f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}/disable",
    )

    assert response.status_code == 403


def test_admin_can_disable() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)

    response = _client(store, service, role=Role.ADMIN).post(
        f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}/disable",
    )

    assert response.status_code == 200


# -- soft delete -----------------------------------------------------------------


def test_owner_can_soft_delete_and_it_then_looks_gone() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)
    client = _client(store, service)

    deleted = client.delete(f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"

    assert client.get(f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}").status_code == 404
    assert client.get(f"/api/v1/workspaces/{WORKSPACE_A}/datasources").json()["total"] == 0
    assert client.post(f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}/test-connection").status_code == 404


def test_admin_cannot_soft_delete() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)

    response = _client(store, service, role=Role.ADMIN).delete(
        f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}",
    )

    assert response.status_code == 403


def test_analyst_cannot_soft_delete() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)

    response = _client(store, service, role=Role.ANALYST).delete(
        f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}",
    )

    assert response.status_code == 403


def test_delete_is_404_across_workspaces() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service, workspace_id=WORKSPACE_A)

    response = _client(store, service, workspace_id=WORKSPACE_B).delete(
        f"/api/v1/workspaces/{WORKSPACE_B}/datasources/{created['id']}",
    )

    assert response.status_code == 404


# -- test-connection diagnostics -------------------------------------------------


def test_test_connection_reports_the_extended_diagnostics() -> None:
    store = FakeDataSourceStore()
    service = FakeOnboardingService(store=store)
    created = _created(store, service)

    response = _client(store, service).post(f"/api/v1/workspaces/{WORKSPACE_A}/datasources/{created['id']}/test-connection")

    assert response.status_code == 200
    body = response.json()
    assert body["ssl_active"] is True
    assert body["accessible_schemas"] == ["public"]
    assert body["latency_ms"] is not None
    assert body["tested_at"] is not None
