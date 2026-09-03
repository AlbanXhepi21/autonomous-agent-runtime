"""The authentication HTTP surface: cookies, CSRF, status codes, and redaction.

Each test builds a small `FastAPI()` app with only the auth router and a
fresh, in-memory `AuthService` (see `_client`) -- no PostgreSQL involved, the
same pattern `tests/api/test_datasources_api.py` already uses. Session-flow
tests reuse one `TestClient` instance across several requests, the same way
a browser would, so its cookie jar carries the session across calls.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.auth import router
from app.composition import get_auth_service, get_settings
from app.config import Settings
from app.identity.email import FileEmailSender
from app.identity.passwords import Argon2PasswordHasher
from app.identity.rate_limit import InMemoryRateLimiter
from app.identity.service import AuthService
from app.identity.store import InMemoryIdentityTokenStore, InMemorySessionStore, InMemoryUserStore

EMAIL = "ada@example.com"
PASSWORD = "correct-horse-1"


def _service(tmp_path: Path, **overrides) -> tuple[AuthService, FileEmailSender]:
    sender = overrides.pop("email_sender", None) or FileEmailSender(tmp_path / ".dev-mail")
    defaults = dict(
        users=InMemoryUserStore(), sessions=InMemorySessionStore(), tokens=InMemoryIdentityTokenStore(),
        password_hasher=Argon2PasswordHasher(), email_sender=sender, rate_limiter=InMemoryRateLimiter(),
        session_idle_ttl_seconds=43_200, session_absolute_ttl_seconds=2_592_000,
        password_reset_ttl_seconds=3_600, email_verification_ttl_seconds=259_200,
        app_base_url="http://localhost:3000",
    )
    defaults.update(overrides)
    return AuthService(**defaults), sender


def _client(service: AuthService, *, cookie_secure: bool = False) -> TestClient:
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides = {
        get_auth_service: lambda: service,
        get_settings: lambda: Settings(security_environment="unknown", auth_cookie_secure=cookie_secure),
    }
    return TestClient(application)


def _register(client: TestClient, *, email: str = EMAIL, password: str = PASSWORD) -> None:
    response = client.post(
        "/api/v1/auth/register", json={"email": email, "password": password, "display_name": "Ada"},
    )
    assert response.status_code == 201, response.text


def _login(client: TestClient, *, email: str = EMAIL, password: str = PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def _extract_token(body: str) -> str:
    line = next(line for line in body.splitlines() if "token=" in line)
    return line.rsplit("token=", 1)[-1].strip()


# -- registration -------------------------------------------------------------


def test_register_returns_the_created_user_without_a_password_hash(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service)

    response = client.post(
        "/api/v1/auth/register", json={"email": EMAIL, "password": PASSWORD, "display_name": "Ada"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == EMAIL
    assert body["email_verified"] is False
    assert "password_hash" not in body
    assert "password" not in body


def test_register_normalizes_email(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service)

    response = client.post(
        "/api/v1/auth/register", json={"email": "  Ada@Example.COM ", "password": PASSWORD, "display_name": "Ada"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "ada@example.com"


def test_register_rejects_a_duplicate_email(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service)
    _register(client)

    response = client.post(
        "/api/v1/auth/register", json={"email": EMAIL.upper(), "password": "another-password-2", "display_name": "Dupe"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "email_already_registered"


def test_register_rejects_an_invalid_email_shape(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service)

    response = client.post(
        "/api/v1/auth/register", json={"email": "not-an-email", "password": PASSWORD, "display_name": "Ada"},
    )

    assert response.status_code == 422


# -- login and cookies ----------------------------------------------------------


def test_login_sets_an_httponly_session_cookie_and_a_readable_csrf_cookie(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service)
    _register(client)

    response = _login(client)

    assert response.status_code == 200
    set_cookie_headers = response.headers.get_list("set-cookie")
    session_cookie = next(header for header in set_cookie_headers if header.startswith("session_token="))
    csrf_cookie = next(header for header in set_cookie_headers if header.startswith("csrf_token="))
    assert "HttpOnly" in session_cookie
    assert "HttpOnly" not in csrf_cookie
    assert "SameSite=lax" in session_cookie


def test_login_cookies_are_not_secure_by_default_but_are_when_configured(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service, cookie_secure=True)
    _register(client)

    response = _login(client)

    session_cookie = next(h for h in response.headers.get_list("set-cookie") if h.startswith("session_token="))
    assert "Secure" in session_cookie


def test_login_fails_with_the_wrong_password(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service)
    _register(client)

    response = _login(client, password="wrong-password")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"
    assert response.headers.get_list("set-cookie") == []


def test_login_rejects_a_disabled_account(tmp_path: Path) -> None:
    users = InMemoryUserStore()
    service, _ = _service(tmp_path, users=users)
    client = _client(service)
    _register(client)
    stored = await_sync(users.get_by_email(EMAIL))
    await_sync(users.set_active(stored.id, is_active=False))

    response = _login(client)

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "account_disabled"


# -- authenticated session flow --------------------------------------------------


def test_me_requires_authentication(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service)

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_login_then_me_then_logout_flow(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service)
    _register(client)
    _login(client)

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL

    # Logging out without the CSRF header is refused.
    unprotected = client.post("/api/v1/auth/logout")
    assert unprotected.status_code == 403
    assert unprotected.json()["detail"]["code"] == "csrf_invalid"

    csrf_token = client.cookies.get("csrf_token")
    logout = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout.status_code == 200

    after_logout = client.get("/api/v1/auth/me")
    assert after_logout.status_code == 401


def test_logout_all_revokes_every_session(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    device_a, device_b = _client(service), _client(service)
    _register(device_a)
    _login(device_a)
    _login(device_b)

    csrf_token = device_a.cookies.get("csrf_token")
    response = device_a.post("/api/v1/auth/logout-all", headers={"X-CSRF-Token": csrf_token})

    assert response.status_code == 200
    assert device_a.get("/api/v1/auth/me").status_code == 401
    assert device_b.get("/api/v1/auth/me").status_code == 401


# -- CSRF -----------------------------------------------------------------------


def test_csrf_rejects_a_header_that_does_not_match_the_cookie(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service)
    _register(client)
    _login(client)

    response = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "some-other-value"})

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "csrf_invalid"


# -- change password --------------------------------------------------------------


def test_change_password_requires_csrf_and_the_correct_current_password(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service)
    _register(client)
    _login(client)
    csrf_token = client.cookies.get("csrf_token")

    wrong_current = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrong", "new_password": "brand-new-password-9"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert wrong_current.status_code == 401

    no_csrf = client.post(
        "/api/v1/auth/change-password", json={"current_password": PASSWORD, "new_password": "brand-new-password-9"},
    )
    assert no_csrf.status_code == 403

    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "brand-new-password-9"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert changed.status_code == 200

    fresh_client = _client(service)
    assert _login(fresh_client, password="brand-new-password-9").status_code == 200


# -- forgot / reset password ---------------------------------------------------------


def test_forgot_password_returns_the_same_generic_response_either_way(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service)
    _register(client)

    registered = client.post("/api/v1/auth/forgot-password", json={"email": EMAIL})
    unregistered = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})

    assert registered.status_code == unregistered.status_code == 200
    assert registered.json() == unregistered.json()


def test_forgot_password_never_returns_a_token(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service)
    _register(client)

    response = client.post("/api/v1/auth/forgot-password", json={"email": EMAIL})

    assert "token" not in json.dumps(response.json())


def test_reset_password_end_to_end_and_then_signs_in_with_the_new_password(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service, sender = _service(tmp_path, email_sender=sender)
    client = _client(service)
    _register(client)
    sender.sent.clear()

    client.post("/api/v1/auth/forgot-password", json={"email": EMAIL})
    token = _extract_token(sender.sent[0].body)

    reset = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "reset-password-42"})
    assert reset.status_code == 200

    assert _login(client, password="reset-password-42").status_code == 200
    assert _login(client, password=PASSWORD).status_code == 401


def test_reset_password_token_is_single_use(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service, sender = _service(tmp_path, email_sender=sender)
    client = _client(service)
    _register(client)
    sender.sent.clear()
    client.post("/api/v1/auth/forgot-password", json={"email": EMAIL})
    token = _extract_token(sender.sent[0].body)
    client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "reset-password-42"})

    second_attempt = client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "another-password-99"},
    )

    assert second_attempt.status_code == 400
    assert second_attempt.json()["detail"]["code"] == "invalid_token"


def test_reset_password_rejects_a_made_up_token(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service)

    response = client.post(
        "/api/v1/auth/reset-password", json={"token": "not-a-real-token", "new_password": "reset-password-42"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_token"


# -- email verification -----------------------------------------------------------


def test_verify_email_resend_requires_csrf_then_confirm_marks_verified(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service, sender = _service(tmp_path, email_sender=sender)
    client = _client(service)
    _register(client)
    _login(client)
    csrf_token = client.cookies.get("csrf_token")

    no_csrf = client.post("/api/v1/auth/verify-email/resend")
    assert no_csrf.status_code == 403

    resend = client.post("/api/v1/auth/verify-email/resend", headers={"X-CSRF-Token": csrf_token})
    assert resend.status_code == 200

    # sender.sent[0] is the registration's own verification email; the resend
    # supersedes it with a fresh token (see AuthService._issue_and_send_token).
    token = _extract_token(sender.sent[-1].body)

    confirm = client.post("/api/v1/auth/verify-email/confirm", json={"token": token})
    assert confirm.status_code == 200

    assert client.get("/api/v1/auth/me").json()["email_verified"] is True


# -- rate limiting ------------------------------------------------------------------


def test_login_is_rate_limited_per_ip(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service)
    _register(client)

    responses = [_login(client, password="wrong-password") for _ in range(11)]

    assert [response.status_code for response in responses[:10]] == [401] * 10
    assert responses[10].status_code == 429
    assert responses[10].json()["detail"]["code"] == "rate_limited"
    assert "Retry-After" in responses[10].headers


def test_register_is_rate_limited_per_ip(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service)

    responses = [
        client.post(
            "/api/v1/auth/register",
            json={"email": f"user{i}@example.com", "password": PASSWORD, "display_name": "User"},
        )
        for i in range(6)
    ]

    assert [response.status_code for response in responses[:5]] == [201] * 5
    assert responses[5].status_code == 429


def test_change_password_is_rate_limited(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service)
    _register(client)
    _login(client)
    csrf_token = client.cookies.get("csrf_token")

    responses = [
        client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "wrong", "new_password": "brand-new-password-9"},
            headers={"X-CSRF-Token": csrf_token},
        )
        for _ in range(11)
    ]

    assert [response.status_code for response in responses[:10]] == [401] * 10
    assert responses[10].status_code == 429
    assert responses[10].json()["detail"]["code"] == "rate_limited"


def test_verify_email_confirm_is_rate_limited(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    client = _client(service)
    _register(client)

    responses = [client.post("/api/v1/auth/verify-email/confirm", json={"token": "not-a-real-token"}) for _ in range(11)]

    assert [response.status_code for response in responses[:10]] == [400] * 10
    assert responses[10].status_code == 429
    assert responses[10].json()["detail"]["code"] == "rate_limited"


# -- sensitive data redaction --------------------------------------------------------


class _CollectingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_password_and_raw_tokens_never_appear_in_logs(tmp_path: Path) -> None:
    """Attaches its own handler directly to app.identity's loggers, independent
    of whatever global logging configuration other tests may have left behind.
    """

    sender = FileEmailSender(tmp_path / ".dev-mail")
    service, sender = _service(tmp_path, email_sender=sender)
    client = _client(service)

    handler = _CollectingHandler()
    service_logger = logging.getLogger("app.identity.service")
    email_logger = logging.getLogger("app.identity.email")
    for logger in (service_logger, email_logger):
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    try:
        _register(client)
        _login(client)
        client.post("/api/v1/auth/forgot-password", json={"email": EMAIL})
    finally:
        for logger in (service_logger, email_logger):
            logger.removeHandler(handler)

    reset_token = _extract_token(sender.sent[-1].body)
    logged_text = "\n".join(
        record.getMessage() + json.dumps(getattr(record, "event_fields", {}), default=str)
        for record in handler.records
    )

    assert PASSWORD not in logged_text
    assert reset_token not in logged_text
    assert len(handler.records) > 0  # the redaction check itself must exercise real log output


def await_sync(coroutine):
    """Run a coroutine to completion from a synchronous test body."""

    return asyncio.run(coroutine)
