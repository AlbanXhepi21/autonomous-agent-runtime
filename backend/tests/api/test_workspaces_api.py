"""The workspace/membership HTTP surface: context resolution, permissions, CSRF.

Builds a small `FastAPI()` app with the auth and workspace routers together
-- no PostgreSQL involved -- and drives everything through real
`/api/v1/auth/*` calls so each test exercises the actual cookie-authenticated
flow, the same way `tests/api/test_auth_api.py` does. Two independent
`TestClient` instances sharing the same backing services simulate two
different signed-in browsers.

Every store-level provider (``get_workspace_store``, ``get_membership_store``,
``get_invitation_store``) is overridden alongside ``get_tenancy_service`` --
some routes (listing workspaces/members) depend on the stores directly
rather than the service, so both must resolve to the *same* instances or a
test would silently read from an unrelated, empty composition singleton.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.auth import router as auth_router
from app.api.routes.workspaces import invitations_router
from app.api.routes.workspaces import router as workspaces_router
from app.composition import (
    get_auth_service,
    get_invitation_store,
    get_membership_store,
    get_tenancy_service,
    get_workspace_store,
)
from app.identity.email import FileEmailSender
from app.identity.passwords import Argon2PasswordHasher
from app.identity.rate_limit import InMemoryRateLimiter
from app.identity.service import AuthService
from app.identity.store import InMemoryIdentityTokenStore, InMemorySessionStore, InMemoryUserStore
from app.tenancy.service import TenancyService
from app.tenancy.store import InMemoryInvitationStore, InMemoryMembershipStore, InMemoryWorkspaceStore

PASSWORD = "correct-horse-1"


def _auth_service(tmp_path: Path) -> AuthService:
    return AuthService(
        users=InMemoryUserStore(), sessions=InMemorySessionStore(), tokens=InMemoryIdentityTokenStore(),
        password_hasher=Argon2PasswordHasher(), email_sender=FileEmailSender(tmp_path / ".auth-mail"),
        rate_limiter=InMemoryRateLimiter(), session_idle_ttl_seconds=43_200, session_absolute_ttl_seconds=2_592_000,
        password_reset_ttl_seconds=3_600, email_verification_ttl_seconds=259_200, app_base_url="http://localhost:3000",
    )


@dataclass
class Tenancy:
    service: TenancyService
    workspaces: InMemoryWorkspaceStore
    memberships: InMemoryMembershipStore
    invitations: InMemoryInvitationStore
    sender: FileEmailSender


def _tenancy(tmp_path: Path) -> Tenancy:
    workspaces, memberships, invitations = InMemoryWorkspaceStore(), InMemoryMembershipStore(), InMemoryInvitationStore()
    sender = FileEmailSender(tmp_path / ".tenancy-mail")
    service = TenancyService(
        workspaces=workspaces, memberships=memberships, invitations=invitations, email_sender=sender,
        invitation_ttl_seconds=604_800, app_base_url="http://localhost:3000",
    )
    return Tenancy(service=service, workspaces=workspaces, memberships=memberships, invitations=invitations, sender=sender)


def _client(auth_service: AuthService, tenancy: Tenancy) -> TestClient:
    application = FastAPI()
    application.include_router(auth_router)
    application.include_router(workspaces_router)
    application.include_router(invitations_router)
    application.dependency_overrides = {
        get_auth_service: lambda: auth_service,
        get_tenancy_service: lambda: tenancy.service,
        get_workspace_store: lambda: tenancy.workspaces,
        get_membership_store: lambda: tenancy.memberships,
        get_invitation_store: lambda: tenancy.invitations,
    }
    return TestClient(application)


def _register_and_login(client: TestClient, email: str, display_name: str = "User") -> dict:
    response = client.post(
        "/api/v1/auth/register", json={"email": email, "password": PASSWORD, "display_name": display_name},
    )
    assert response.status_code == 201, response.text
    user = response.json()
    login = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return user


def _csrf(client: TestClient) -> dict:
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def _extract_token(body: str) -> str:
    line = next(line for line in body.splitlines() if "token=" in line)
    return line.rsplit("token=", 1)[-1].strip()


# -- create / list / read --------------------------------------------------------


def test_create_workspace_makes_the_creator_an_owner(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    client = _client(auth_service, tenancy)
    _register_and_login(client, "owner@example.com")

    response = client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(client))

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["slug"] == "acme"
    assert body["is_active"] is True

    members = client.get(f"/api/v1/workspaces/{body['id']}/members")
    assert members.status_code == 200
    assert [item["role"] for item in members.json()["items"]] == ["owner"]


def test_create_workspace_rejects_a_duplicate_slug(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    client = _client(auth_service, tenancy)
    _register_and_login(client, "owner@example.com")
    client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(client))

    response = client.post("/api/v1/workspaces", json={"name": "Acme Two", "slug": "ACME"}, headers=_csrf(client))

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "slug_already_exists"


def test_list_my_workspaces_returns_only_workspaces_the_caller_belongs_to(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    alice, bob = _client(auth_service, tenancy), _client(auth_service, tenancy)
    _register_and_login(alice, "alice@example.com")
    _register_and_login(bob, "bob@example.com")
    alice.post("/api/v1/workspaces", json={"name": "Alice Co", "slug": "alice-co"}, headers=_csrf(alice))
    bob.post("/api/v1/workspaces", json={"name": "Bob Co", "slug": "bob-co"}, headers=_csrf(bob))

    response = alice.get("/api/v1/workspaces")

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["items"]] == ["alice-co"]


# -- tenant context resolution -------------------------------------------------


def test_unknown_workspace_returns_404(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    client = _client(auth_service, tenancy)
    _register_and_login(client, "owner@example.com")

    response = client.get(f"/api/v1/workspaces/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "unknown_workspace"


def test_a_workspace_that_exists_but_you_are_not_a_member_of_also_returns_404(tmp_path: Path) -> None:
    """A caller with no membership cannot distinguish "does not exist" from
    "exists but you were never invited" -- both are 404.
    """

    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    owner_client, outsider_client = _client(auth_service, tenancy), _client(auth_service, tenancy)
    _register_and_login(owner_client, "owner@example.com")
    _register_and_login(outsider_client, "outsider@example.com")
    created = owner_client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(owner_client)).json()

    response = outsider_client.get(f"/api/v1/workspaces/{created['id']}")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "unknown_workspace"


def test_a_disabled_membership_returns_403_not_404(tmp_path: Path) -> None:
    """Unlike "never a member," a removed member already knows the workspace
    exists, so this is 403, not 404.
    """

    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    owner_client, viewer_client = _client(auth_service, tenancy), _client(auth_service, tenancy)
    _register_and_login(owner_client, "owner@example.com")
    viewer = _register_and_login(viewer_client, "viewer@example.com")
    workspace = owner_client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(owner_client)).json()
    invite = owner_client.post(
        f"/api/v1/workspaces/{workspace['id']}/members/invite",
        json={"email": "viewer@example.com", "role": "viewer"}, headers=_csrf(owner_client),
    )
    assert invite.status_code == 201, invite.text
    token = _extract_token(tenancy.sender.sent[-1].body)
    accepted = viewer_client.post("/api/v1/invitations/accept", json={"token": token})
    assert accepted.status_code == 200, accepted.text

    owner_client.delete(f"/api/v1/workspaces/{workspace['id']}/members/{viewer['id']}", headers=_csrf(owner_client))

    response = viewer_client.get(f"/api/v1/workspaces/{workspace['id']}")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "membership_disabled"


# -- permission enforcement ------------------------------------------------------


def test_viewer_cannot_invite_members(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    owner_client, viewer_client = _client(auth_service, tenancy), _client(auth_service, tenancy)
    _register_and_login(owner_client, "owner@example.com")
    _register_and_login(viewer_client, "viewer@example.com")
    workspace = owner_client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(owner_client)).json()
    owner_client.post(
        f"/api/v1/workspaces/{workspace['id']}/members/invite",
        json={"email": "viewer@example.com", "role": "viewer"}, headers=_csrf(owner_client),
    )
    token = _extract_token(tenancy.sender.sent[-1].body)
    viewer_client.post("/api/v1/invitations/accept", json={"token": token})

    response = viewer_client.post(
        f"/api/v1/workspaces/{workspace['id']}/members/invite",
        json={"email": "someone@example.com", "role": "viewer"}, headers=_csrf(viewer_client),
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "permission_denied"


def test_analyst_cannot_manage_data_sources_permission_but_can_read(tmp_path: Path) -> None:
    """A smoke check that require_permission actually varies by role, not just
    by "member or not."
    """

    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    owner_client, analyst_client = _client(auth_service, tenancy), _client(auth_service, tenancy)
    _register_and_login(owner_client, "owner@example.com")
    _register_and_login(analyst_client, "analyst@example.com")
    workspace = owner_client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(owner_client)).json()
    owner_client.post(
        f"/api/v1/workspaces/{workspace['id']}/members/invite",
        json={"email": "analyst@example.com", "role": "analyst"}, headers=_csrf(owner_client),
    )
    token = _extract_token(tenancy.sender.sent[-1].body)
    analyst_client.post("/api/v1/invitations/accept", json={"token": token})

    can_read = analyst_client.get(f"/api/v1/workspaces/{workspace['id']}")
    assert can_read.status_code == 200

    cannot_update_settings = analyst_client.patch(
        f"/api/v1/workspaces/{workspace['id']}", json={"name": "Renamed", "expected_version": 1},
        headers=_csrf(analyst_client),
    )
    assert cannot_update_settings.status_code == 403


# -- CSRF -----------------------------------------------------------------------


def test_update_workspace_requires_csrf(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    client = _client(auth_service, tenancy)
    _register_and_login(client, "owner@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(client)).json()

    response = client.patch(
        f"/api/v1/workspaces/{workspace['id']}", json={"name": "Renamed", "expected_version": 1},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "csrf_invalid"


# -- invite / accept flow --------------------------------------------------------


def test_full_invite_and_accept_flow(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    owner_client, invitee_client = _client(auth_service, tenancy), _client(auth_service, tenancy)
    _register_and_login(owner_client, "owner@example.com")
    workspace = owner_client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(owner_client)).json()

    invite = owner_client.post(
        f"/api/v1/workspaces/{workspace['id']}/members/invite",
        json={"email": "new-analyst@example.com", "role": "analyst"}, headers=_csrf(owner_client),
    )
    assert invite.status_code == 201
    assert "token" not in invite.text  # never returned via the API

    _register_and_login(invitee_client, "new-analyst@example.com")
    token = _extract_token(tenancy.sender.sent[-1].body)
    accept = invitee_client.post("/api/v1/invitations/accept", json={"token": token})

    assert accept.status_code == 200
    assert accept.json()["role"] == "analyst"

    members = owner_client.get(f"/api/v1/workspaces/{workspace['id']}/members")
    assert sorted(item["role"] for item in members.json()["items"]) == ["analyst", "owner"]


def test_duplicate_invitation_is_rejected(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    client = _client(auth_service, tenancy)
    _register_and_login(client, "owner@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(client)).json()
    client.post(
        f"/api/v1/workspaces/{workspace['id']}/members/invite",
        json={"email": "someone@example.com", "role": "viewer"}, headers=_csrf(client),
    )

    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/members/invite",
        json={"email": "someone@example.com", "role": "analyst"}, headers=_csrf(client),
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "duplicate_invitation"


def test_wrong_email_cannot_accept_the_invitation(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    owner_client, wrong_client = _client(auth_service, tenancy), _client(auth_service, tenancy)
    _register_and_login(owner_client, "owner@example.com")
    _register_and_login(wrong_client, "wrong-person@example.com")
    workspace = owner_client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(owner_client)).json()
    owner_client.post(
        f"/api/v1/workspaces/{workspace['id']}/members/invite",
        json={"email": "intended@example.com", "role": "viewer"}, headers=_csrf(owner_client),
    )
    token = _extract_token(tenancy.sender.sent[-1].body)

    response = wrong_client.post("/api/v1/invitations/accept", json={"token": token})

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "invitation_email_mismatch"


# -- lifecycle rules through the API -----------------------------------------------


def test_last_owner_cannot_leave_via_the_api(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    client = _client(auth_service, tenancy)
    _register_and_login(client, "owner@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(client)).json()

    response = client.post(f"/api/v1/workspaces/{workspace['id']}/leave", headers=_csrf(client))

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "last_owner"


def test_admin_cannot_remove_an_owner_via_the_api(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    owner_client, admin_client = _client(auth_service, tenancy), _client(auth_service, tenancy)
    owner = _register_and_login(owner_client, "owner@example.com")
    _register_and_login(admin_client, "admin@example.com")
    workspace = owner_client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(owner_client)).json()
    owner_client.post(
        f"/api/v1/workspaces/{workspace['id']}/members/invite",
        json={"email": "admin@example.com", "role": "admin"}, headers=_csrf(owner_client),
    )
    token = _extract_token(tenancy.sender.sent[-1].body)
    admin_client.post("/api/v1/invitations/accept", json={"token": token})

    response = admin_client.delete(
        f"/api/v1/workspaces/{workspace['id']}/members/{owner['id']}", headers=_csrf(admin_client),
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "owner_required"


def test_transfer_ownership_via_the_api(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    owner_client, admin_client = _client(auth_service, tenancy), _client(auth_service, tenancy)
    admin = _register_and_login(admin_client, "admin@example.com")
    _register_and_login(owner_client, "owner@example.com")
    workspace = owner_client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(owner_client)).json()
    owner_client.post(
        f"/api/v1/workspaces/{workspace['id']}/members/invite",
        json={"email": "admin@example.com", "role": "admin"}, headers=_csrf(owner_client),
    )
    token = _extract_token(tenancy.sender.sent[-1].body)
    admin_client.post("/api/v1/invitations/accept", json={"token": token})

    response = owner_client.post(
        f"/api/v1/workspaces/{workspace['id']}/transfer-ownership",
        json={"to_user_id": admin["id"]}, headers=_csrf(owner_client),
    )

    assert response.status_code == 200
    assert response.json()["role"] == "owner"
    # The original owner is now free to leave -- they are no longer an owner.
    leave = owner_client.post(f"/api/v1/workspaces/{workspace['id']}/leave", headers=_csrf(owner_client))
    assert leave.status_code == 200


def test_deactivate_workspace_blocks_further_access(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    client = _client(auth_service, tenancy)
    _register_and_login(client, "owner@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(client)).json()

    deactivate = client.post(f"/api/v1/workspaces/{workspace['id']}/deactivate", headers=_csrf(client))
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False

    response = client.get(f"/api/v1/workspaces/{workspace['id']}")
    assert response.status_code == 404


# -- tenant settings: validation and optimistic concurrency --------------------


def test_create_workspace_rejects_an_unknown_timezone(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    client = _client(auth_service, tenancy)
    _register_and_login(client, "owner@example.com")

    response = client.post(
        "/api/v1/workspaces",
        json={"name": "Acme", "slug": "acme", "default_timezone": "Mars/Olympus_Mons"},
        headers=_csrf(client),
    )

    assert response.status_code == 422


def test_create_workspace_rejects_an_unknown_currency(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    client = _client(auth_service, tenancy)
    _register_and_login(client, "owner@example.com")

    response = client.post(
        "/api/v1/workspaces",
        json={"name": "Acme", "slug": "acme", "default_currency": "ZZZ"},
        headers=_csrf(client),
    )

    assert response.status_code == 422


def test_create_workspace_rejects_a_malformed_locale(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    client = _client(auth_service, tenancy)
    _register_and_login(client, "owner@example.com")

    response = client.post(
        "/api/v1/workspaces",
        json={"name": "Acme", "slug": "acme", "default_locale": "not_a_locale!!"},
        headers=_csrf(client),
    )

    assert response.status_code == 422


def test_update_workspace_applies_fiscal_and_format_settings(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    client = _client(auth_service, tenancy)
    _register_and_login(client, "owner@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(client)).json()

    response = client.patch(
        f"/api/v1/workspaces/{workspace['id']}",
        json={"expected_version": 1, "fiscal_year_start_month": 4, "number_format": "1.234,56", "date_format": "DD/MM/YYYY"},
        headers=_csrf(client),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["fiscal_year_start_month"] == 4
    assert body["number_format"] == "1.234,56"
    assert body["date_format"] == "DD/MM/YYYY"
    assert body["version"] == 2


def test_update_workspace_rejects_a_stale_expected_version(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    client = _client(auth_service, tenancy)
    _register_and_login(client, "owner@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(client)).json()
    client.patch(
        f"/api/v1/workspaces/{workspace['id']}", json={"expected_version": 1, "name": "Acme Renamed"},
        headers=_csrf(client),
    )

    response = client.patch(
        f"/api/v1/workspaces/{workspace['id']}", json={"expected_version": 1, "name": "Acme Again"},
        headers=_csrf(client),
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "version_conflict"
    assert response.json()["detail"]["expected_version"] == 1
    assert response.json()["detail"]["actual_version"] == 2


# -- report preferences ---------------------------------------------------------


def test_report_preferences_default_to_evidence_appendix_enabled(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    client = _client(auth_service, tenancy)
    _register_and_login(client, "owner@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(client)).json()

    response = client.get(f"/api/v1/workspaces/{workspace['id']}/report-preferences")

    assert response.status_code == 200
    body = response.json()
    assert body["evidence_appendix_enabled"] is True
    assert body["default_template"] is None
    assert body["version"] == 1


def test_update_report_preferences_changes_presentation_defaults(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    client = _client(auth_service, tenancy)
    _register_and_login(client, "owner@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(client)).json()

    response = client.patch(
        f"/api/v1/workspaces/{workspace['id']}/report-preferences",
        json={
            "expected_version": 1, "default_template": "monthly_business_review", "default_output_format": "pdf",
            "default_narrative_policy": "exclude", "technical_sql_appendix_enabled": True,
        },
        headers=_csrf(client),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["default_template"] == "monthly_business_review"
    assert body["default_output_format"] == "pdf"
    assert body["technical_sql_appendix_enabled"] is True
    assert body["version"] == 2


def test_update_report_preferences_rejects_an_unknown_template_id(tmp_path: Path) -> None:
    """``default_template`` is a free-text column, but its value has to name a
    template the registry actually publishes -- otherwise a workspace could
    configure a default that fails every time a report is published."""

    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    client = _client(auth_service, tenancy)
    _register_and_login(client, "owner@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(client)).json()

    response = client.patch(
        f"/api/v1/workspaces/{workspace['id']}/report-preferences",
        json={"expected_version": 1, "default_template": "not_a_real_template"},
        headers=_csrf(client),
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "unknown_template"

    unchanged = client.get(f"/api/v1/workspaces/{workspace['id']}/report-preferences")
    assert unchanged.json()["default_template"] is None


def test_analyst_cannot_update_report_preferences_but_can_read_them(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    owner_client, analyst_client = _client(auth_service, tenancy), _client(auth_service, tenancy)
    _register_and_login(owner_client, "owner@example.com")
    _register_and_login(analyst_client, "analyst@example.com")
    workspace = owner_client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(owner_client)).json()
    owner_client.post(
        f"/api/v1/workspaces/{workspace['id']}/members/invite",
        json={"email": "analyst@example.com", "role": "analyst"}, headers=_csrf(owner_client),
    )
    token = _extract_token(tenancy.sender.sent[-1].body)
    analyst_client.post("/api/v1/invitations/accept", json={"token": token})

    can_read = analyst_client.get(f"/api/v1/workspaces/{workspace['id']}/report-preferences")
    assert can_read.status_code == 200

    cannot_update = analyst_client.patch(
        f"/api/v1/workspaces/{workspace['id']}/report-preferences",
        json={"expected_version": 1, "default_template": "x"}, headers=_csrf(analyst_client),
    )
    assert cannot_update.status_code == 403


def test_report_preferences_are_not_visible_across_tenants(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    tenant_a, tenant_b = _client(auth_service, tenancy), _client(auth_service, tenancy)
    _register_and_login(tenant_a, "a@example.com")
    _register_and_login(tenant_b, "b@example.com")
    workspace_a = tenant_a.post("/api/v1/workspaces", json={"name": "A Co", "slug": "a-co"}, headers=_csrf(tenant_a)).json()
    tenant_b.post("/api/v1/workspaces", json={"name": "B Co", "slug": "b-co"}, headers=_csrf(tenant_b)).json()
    tenant_a.patch(
        f"/api/v1/workspaces/{workspace_a['id']}/report-preferences",
        json={"expected_version": 1, "default_template": "a-only-template"}, headers=_csrf(tenant_a),
    )

    response = tenant_b.get(f"/api/v1/workspaces/{workspace_a['id']}/report-preferences")

    assert response.status_code == 404


# -- audit log --------------------------------------------------------------------


def test_audit_log_records_a_settings_change(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    client = _client(auth_service, tenancy)
    owner = _register_and_login(client, "owner@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(client)).json()
    client.patch(
        f"/api/v1/workspaces/{workspace['id']}", json={"expected_version": 1, "name": "Acme Renamed"},
        headers=_csrf(client),
    )

    response = client.get(f"/api/v1/workspaces/{workspace['id']}/audit-log")

    assert response.status_code == 200
    events = [item["event_type"] for item in response.json()["items"]]
    assert "tenancy_workspace_settings_updated" in events
    assert response.json()["items"][0]["actor_user_id"] == owner["id"]


def test_analyst_cannot_view_the_audit_log(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    owner_client, analyst_client = _client(auth_service, tenancy), _client(auth_service, tenancy)
    _register_and_login(owner_client, "owner@example.com")
    _register_and_login(analyst_client, "analyst@example.com")
    workspace = owner_client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(owner_client)).json()
    owner_client.post(
        f"/api/v1/workspaces/{workspace['id']}/members/invite",
        json={"email": "analyst@example.com", "role": "analyst"}, headers=_csrf(owner_client),
    )
    token = _extract_token(tenancy.sender.sent[-1].body)
    analyst_client.post("/api/v1/invitations/accept", json={"token": token})

    response = analyst_client.get(f"/api/v1/workspaces/{workspace['id']}/audit-log")

    assert response.status_code == 403


def test_audit_log_is_not_visible_across_tenants(tmp_path: Path) -> None:
    auth_service, tenancy = _auth_service(tmp_path), _tenancy(tmp_path)
    tenant_a, tenant_b = _client(auth_service, tenancy), _client(auth_service, tenancy)
    _register_and_login(tenant_a, "a@example.com")
    _register_and_login(tenant_b, "b@example.com")
    workspace_a = tenant_a.post("/api/v1/workspaces", json={"name": "A Co", "slug": "a-co"}, headers=_csrf(tenant_a)).json()
    tenant_b.post("/api/v1/workspaces", json={"name": "B Co", "slug": "b-co"}, headers=_csrf(tenant_b)).json()
    tenant_a.patch(
        f"/api/v1/workspaces/{workspace_a['id']}", json={"expected_version": 1, "name": "Renamed"},
        headers=_csrf(tenant_a),
    )

    response = tenant_b.get(f"/api/v1/workspaces/{workspace_a['id']}/audit-log")

    assert response.status_code == 404
