"""The user profile/settings HTTP surface: display name, locale preferences,
profile image (through the existing artifact system), and the two-step,
password-reauthenticated email-change flow.

Same pattern as ``tests/api/test_workspaces_api.py``: a small ``FastAPI()``
app with the real routers, driven through actual ``/api/v1/auth/*`` calls so
each test exercises the real cookie-authenticated flow rather than a faked
tenant context.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.auth import router as auth_router
from app.api.routes.users import router as users_router
from app.api.routes.workspaces import router as workspaces_router
from app.artifacts.store import ArtifactStore, WorkspaceArtifactStore
from app.composition import get_artifact_store, get_auth_service, get_tenancy_service
from app.composition import get_workspace as get_environment_workspace
from app.environment.workspace import Workspace
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
class Environment:
    """Shared backing stores -- two clients built from the same ``Environment``
    simulate two browsers seeing the same workspaces and artifacts, the way
    two clients built from the same ``Tenancy`` do in test_workspaces_api.py.
    """

    tenancy: TenancyService
    workspace: Workspace
    artifacts: ArtifactStore


def _environment(tmp_path: Path) -> Environment:
    workspace = Workspace(tmp_path / "env")
    artifacts = WorkspaceArtifactStore(workspace, max_artifact_bytes=10_485_760)
    tenancy = TenancyService(
        workspaces=InMemoryWorkspaceStore(), memberships=InMemoryMembershipStore(),
        invitations=InMemoryInvitationStore(), email_sender=FileEmailSender(tmp_path / ".tenancy-mail"),
        invitation_ttl_seconds=604_800, app_base_url="http://localhost:3000",
    )
    return Environment(tenancy=tenancy, workspace=workspace, artifacts=artifacts)


def _client(auth_service: AuthService, environment: Environment) -> TestClient:
    application = FastAPI()
    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(workspaces_router)
    application.dependency_overrides = {
        get_auth_service: lambda: auth_service,
        get_tenancy_service: lambda: environment.tenancy,
        get_artifact_store: lambda: environment.artifacts,
        get_environment_workspace: lambda: environment.workspace,
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


# -- profile settings ---------------------------------------------------------


def test_get_my_settings_reflects_the_registered_account(tmp_path: Path) -> None:
    client = _client(_auth_service(tmp_path), _environment(tmp_path))
    _register_and_login(client, "ada@example.com", display_name="Ada Lovelace")

    response = client.get("/api/v1/users/me")

    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Ada Lovelace"
    assert body["preferred_timezone"] == "UTC"
    assert body["preferred_locale"] == "en-US"
    assert "password_hash" not in body


def test_update_my_settings_applies_a_partial_change(tmp_path: Path) -> None:
    client = _client(_auth_service(tmp_path), _environment(tmp_path))
    _register_and_login(client, "ada@example.com")

    response = client.patch(
        "/api/v1/users/me", json={"preferred_timezone": "America/New_York"}, headers=_csrf(client),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["preferred_timezone"] == "America/New_York"
    assert body["display_name"] == "User"  # untouched


def test_update_my_settings_rejects_an_unknown_timezone(tmp_path: Path) -> None:
    client = _client(_auth_service(tmp_path), _environment(tmp_path))
    _register_and_login(client, "ada@example.com")

    response = client.patch(
        "/api/v1/users/me", json={"preferred_timezone": "Mars/Olympus_Mons"}, headers=_csrf(client),
    )

    assert response.status_code == 422


def test_update_my_settings_rejects_a_malformed_locale(tmp_path: Path) -> None:
    client = _client(_auth_service(tmp_path), _environment(tmp_path))
    _register_and_login(client, "ada@example.com")

    response = client.patch(
        "/api/v1/users/me", json={"preferred_locale": "not_a_locale!!"}, headers=_csrf(client),
    )

    assert response.status_code == 422


def test_update_my_settings_rejects_an_unrecognized_field(tmp_path: Path) -> None:
    """extra="forbid": a stale or misspelled field is a 422, not silently dropped."""

    client = _client(_auth_service(tmp_path), _environment(tmp_path))
    _register_and_login(client, "ada@example.com")

    response = client.patch("/api/v1/users/me", json={"is_admin": True}, headers=_csrf(client))

    assert response.status_code == 422


def test_update_my_settings_requires_csrf(tmp_path: Path) -> None:
    client = _client(_auth_service(tmp_path), _environment(tmp_path))
    _register_and_login(client, "ada@example.com")

    response = client.patch("/api/v1/users/me", json={"display_name": "New Name"})

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "csrf_invalid"


# -- profile image (through the existing artifact system) --------------------


def test_set_profile_image_registers_an_artifact_and_points_the_profile_at_it(tmp_path: Path) -> None:
    client = _client(_auth_service(tmp_path), _environment(tmp_path))
    _register_and_login(client, "ada@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(client)).json()

    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/profile-image",
        files={"file": ("avatar.png", b"\x89PNG\r\n\x1a\n" + b"0" * 100, "image/png")},
        headers=_csrf(client),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["profile_image_artifact_id"] is not None
    assert body["profile_image_workspace_id"] == workspace["id"]

    settings = client.get("/api/v1/users/me").json()
    assert settings["profile_image_artifact_id"] == body["profile_image_artifact_id"]


def test_set_profile_image_rejects_an_unsupported_type(tmp_path: Path) -> None:
    client = _client(_auth_service(tmp_path), _environment(tmp_path))
    _register_and_login(client, "ada@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(client)).json()

    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/profile-image",
        files={"file": ("avatar.svg", b"<svg></svg>", "image/svg+xml")},
        headers=_csrf(client),
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "unsupported_image_type"


def test_set_profile_image_requires_membership_in_the_target_workspace(tmp_path: Path) -> None:
    auth_service = _auth_service(tmp_path)
    environment = _environment(tmp_path)
    owner_client, outsider_client = _client(auth_service, environment), _client(auth_service, environment)
    _register_and_login(owner_client, "owner@example.com")
    _register_and_login(outsider_client, "outsider@example.com")
    workspace = owner_client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme"}, headers=_csrf(owner_client)).json()

    response = outsider_client.post(
        f"/api/v1/workspaces/{workspace['id']}/profile-image",
        files={"file": ("avatar.png", b"\x89PNG\r\n\x1a\n" + b"0" * 100, "image/png")},
        headers=_csrf(outsider_client),
    )

    assert response.status_code == 404


# -- email change ------------------------------------------------------------


def test_email_change_requires_the_correct_current_password(tmp_path: Path) -> None:
    client = _client(_auth_service(tmp_path), _environment(tmp_path))
    _register_and_login(client, "ada@example.com")

    response = client.post(
        "/api/v1/users/me/email-change/request",
        json={"new_email": "ada-new@example.com", "current_password": "wrong-password"},
        headers=_csrf(client),
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"


def test_email_change_rejects_an_address_already_registered(tmp_path: Path) -> None:
    auth_service = _auth_service(tmp_path)
    environment = _environment(tmp_path)
    client = _client(auth_service, environment)
    _register_and_login(client, "ada@example.com")
    other_client = _client(auth_service, environment)
    _register_and_login(other_client, "grace@example.com")

    response = client.post(
        "/api/v1/users/me/email-change/request",
        json={"new_email": "grace@example.com", "current_password": PASSWORD},
        headers=_csrf(client),
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "email_already_registered"


def test_email_change_request_requires_csrf(tmp_path: Path) -> None:
    client = _client(_auth_service(tmp_path), _environment(tmp_path))
    _register_and_login(client, "ada@example.com")

    response = client.post(
        "/api/v1/users/me/email-change/request",
        json={"new_email": "ada-new@example.com", "current_password": PASSWORD},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "csrf_invalid"


def test_full_email_change_flow_updates_the_address_and_signs_out_other_sessions(tmp_path: Path) -> None:
    auth_service = _auth_service(tmp_path)
    client = _client(auth_service, _environment(tmp_path))
    _register_and_login(client, "ada@example.com")

    request = client.post(
        "/api/v1/users/me/email-change/request",
        json={"new_email": "ada-new@example.com", "current_password": PASSWORD},
        headers=_csrf(client),
    )
    assert request.status_code == 200, request.text
    assert "token" not in request.text  # never returned via the API

    mail_dir = tmp_path / ".auth-mail"
    sent = sorted(mail_dir.glob("*.eml"), key=lambda path: path.stat().st_mtime)
    token = _extract_token(sent[-1].read_text())

    confirm = client.post("/api/v1/users/me/email-change/confirm", json={"token": token})

    assert confirm.status_code == 200, confirm.text
    body = confirm.json()
    assert body["email"] == "ada-new@example.com"
    assert body["pending_email"] is None
    assert body["email_verified"] is True

    # The old session was revoked as part of the change; this client must sign in again.
    me = client.get("/api/v1/users/me")
    assert me.status_code == 401


def test_confirm_email_change_rejects_an_invalid_token(tmp_path: Path) -> None:
    client = _client(_auth_service(tmp_path), _environment(tmp_path))
    _register_and_login(client, "ada@example.com")

    response = client.post("/api/v1/users/me/email-change/confirm", json={"token": "not-a-real-token"})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_token"
