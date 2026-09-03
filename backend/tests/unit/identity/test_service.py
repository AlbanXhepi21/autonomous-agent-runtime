"""AuthService behavior over in-memory identity storage.

No PostgreSQL involved -- this exercises registration, login, sessions,
password management, and recovery/verification tokens purely against
``InMemoryUserStore``/``InMemorySessionStore``/``InMemoryIdentityTokenStore``
and a real ``Argon2PasswordHasher``, so it runs everywhere the API tests do.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from app.audit.store import InMemoryAuditLogStore
from app.identity.contracts import TokenPurpose
from app.identity.email import FileEmailSender
from app.identity.passwords import Argon2PasswordHasher
from app.identity.rate_limit import InMemoryRateLimiter
from app.identity.service import (
    AccountDisabledError,
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    SameEmailError,
    SessionInvalidError,
    TokenInvalidError,
    WeakPasswordError,
)
from app.identity.store import InMemoryIdentityTokenStore, InMemorySessionStore, InMemoryUserStore
from app.identity.tokens import generate_token, hash_token


def make_service(tmp_path: Path, **overrides) -> AuthService:
    defaults = dict(
        users=InMemoryUserStore(), sessions=InMemorySessionStore(), tokens=InMemoryIdentityTokenStore(),
        password_hasher=Argon2PasswordHasher(), email_sender=FileEmailSender(tmp_path / ".dev-mail"),
        rate_limiter=InMemoryRateLimiter(), session_idle_ttl_seconds=43_200,
        session_absolute_ttl_seconds=2_592_000, password_reset_ttl_seconds=3_600,
        email_verification_ttl_seconds=259_200, app_base_url="http://localhost:3000",
    )
    defaults.update(overrides)
    return AuthService(**defaults)


# -- registration ------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_creates_an_inactive_unverified_looking_account_correctly(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    user = await service.register(email="Ada@Example.com", password="correct-horse-1", display_name="Ada")

    assert user.email == "ada@example.com"
    assert user.is_active is True
    assert user.email_verified is False
    assert user.password_hash != "correct-horse-1"


@pytest.mark.asyncio
async def test_register_normalizes_email_case_and_whitespace(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    user = await service.register(email="  Ada@Example.COM  ", password="correct-horse-1", display_name="Ada")

    assert user.email == "ada@example.com"


@pytest.mark.asyncio
async def test_register_rejects_a_duplicate_normalized_email(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")

    with pytest.raises(EmailAlreadyRegisteredError):
        await service.register(email="ADA@EXAMPLE.COM", password="another-password-2", display_name="Ada Two")


@pytest.mark.asyncio
async def test_register_rejects_a_short_password(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    with pytest.raises(WeakPasswordError):
        await service.register(email="ada@example.com", password="short", display_name="Ada")


@pytest.mark.asyncio
async def test_register_sends_exactly_one_verification_email(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)

    await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")

    assert len(sender.sent) == 1
    assert sender.sent[0].to == "ada@example.com"
    assert "verify" in sender.sent[0].subject.lower()


# -- login --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_succeeds_with_correct_credentials(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")

    user, session_token, csrf_token = await service.login(
        email="ada@example.com", password="correct-horse-1", user_agent="pytest", ip_address="127.0.0.1",
    )

    assert user.email == "ada@example.com"
    assert session_token and csrf_token and session_token != csrf_token
    assert user.last_login_at is not None


@pytest.mark.asyncio
async def test_login_fails_with_wrong_password(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")

    with pytest.raises(InvalidCredentialsError):
        await service.login(email="ada@example.com", password="wrong-password", user_agent=None, ip_address=None)


@pytest.mark.asyncio
async def test_login_fails_for_an_unregistered_email_with_the_same_error(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    with pytest.raises(InvalidCredentialsError):
        await service.login(email="nobody@example.com", password="whatever-1", user_agent=None, ip_address=None)


@pytest.mark.asyncio
async def test_login_rejects_a_disabled_account(tmp_path: Path) -> None:
    users = InMemoryUserStore()
    service = make_service(tmp_path, users=users)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    await users.set_active(user.id, is_active=False)

    with pytest.raises(AccountDisabledError):
        await service.login(email="ada@example.com", password="correct-horse-1", user_agent=None, ip_address=None)


# -- session authentication and expiration -------------------------------------


@pytest.mark.asyncio
async def test_validate_session_returns_the_session_for_a_fresh_login(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    _, session_token, _ = await service.login(
        email="ada@example.com", password="correct-horse-1", user_agent=None, ip_address=None,
    )

    session = await service.validate_session(session_token=session_token)

    assert session.revoked_at is None
    user = await service.user_for_session(session)
    assert user.email == "ada@example.com"


@pytest.mark.asyncio
async def test_validate_session_rejects_an_unknown_token(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    with pytest.raises(SessionInvalidError):
        await service.validate_session(session_token="not-a-real-token")


@pytest.mark.asyncio
async def test_validate_session_rejects_a_session_past_its_idle_timeout(tmp_path: Path) -> None:
    sessions = InMemorySessionStore()
    service = make_service(tmp_path, sessions=sessions, session_idle_ttl_seconds=1)
    await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    _, session_token, _ = await service.login(
        email="ada@example.com", password="correct-horse-1", user_agent=None, ip_address=None,
    )
    session = await service.validate_session(session_token=session_token)
    # Simulate inactivity by rewinding last_seen_at past the 1-second idle budget.
    await sessions.touch(session.id, last_seen_at=datetime.now(UTC) - timedelta(seconds=5))

    with pytest.raises(SessionInvalidError):
        await service.validate_session(session_token=session_token)


@pytest.mark.asyncio
async def test_validate_session_rejects_a_session_past_its_absolute_lifetime(tmp_path: Path) -> None:
    """A session created with an already-past `expires_at` -- the same shape a
    long-idle-but-still-ticking absolute cap eventually produces -- is refused.
    """

    sessions = InMemorySessionStore()
    service = make_service(tmp_path, sessions=sessions)
    raw_token = generate_token()
    await sessions.create(
        user_id=uuid4(), token_hash=hash_token(raw_token), csrf_token_hash=hash_token(generate_token()),
        expires_at=datetime.now(UTC) - timedelta(seconds=1), user_agent=None, ip_address=None,
    )

    with pytest.raises(SessionInvalidError):
        await service.validate_session(session_token=raw_token)


# -- logout / revocation -------------------------------------------------------


@pytest.mark.asyncio
async def test_logout_revokes_only_the_current_session(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    _, token_a, _ = await service.login(email="ada@example.com", password="correct-horse-1", user_agent=None, ip_address=None)
    _, token_b, _ = await service.login(email="ada@example.com", password="correct-horse-1", user_agent=None, ip_address=None)
    session_a = await service.validate_session(session_token=token_a)

    await service.logout(session_id=session_a.id)

    with pytest.raises(SessionInvalidError):
        await service.validate_session(session_token=token_a)
    # The other device's session is untouched.
    await service.validate_session(session_token=token_b)


@pytest.mark.asyncio
async def test_logout_all_revokes_every_session_for_the_user(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    _, token_a, _ = await service.login(email="ada@example.com", password="correct-horse-1", user_agent=None, ip_address=None)
    _, token_b, _ = await service.login(email="ada@example.com", password="correct-horse-1", user_agent=None, ip_address=None)

    count = await service.logout_all(user_id=user.id)

    assert count == 2
    for token in (token_a, token_b):
        with pytest.raises(SessionInvalidError):
            await service.validate_session(session_token=token)


# -- password change -----------------------------------------------------------


@pytest.mark.asyncio
async def test_change_password_requires_the_correct_current_password(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    _, token, _ = await service.login(email="ada@example.com", password="correct-horse-1", user_agent=None, ip_address=None)
    session = await service.validate_session(session_token=token)

    with pytest.raises(InvalidCredentialsError):
        await service.change_password(
            user_id=user.id, current_password="wrong-password", new_password="new-password-2", keep_session_id=session.id,
        )


@pytest.mark.asyncio
async def test_change_password_lets_the_new_password_authenticate(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    _, token, _ = await service.login(email="ada@example.com", password="correct-horse-1", user_agent=None, ip_address=None)
    session = await service.validate_session(session_token=token)

    await service.change_password(
        user_id=user.id, current_password="correct-horse-1", new_password="brand-new-password-9", keep_session_id=session.id,
    )

    await service.login(email="ada@example.com", password="brand-new-password-9", user_agent=None, ip_address=None)
    with pytest.raises(InvalidCredentialsError):
        await service.login(email="ada@example.com", password="correct-horse-1", user_agent=None, ip_address=None)


@pytest.mark.asyncio
async def test_change_password_revokes_other_sessions_but_keeps_the_current_one(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    _, token_a, _ = await service.login(email="ada@example.com", password="correct-horse-1", user_agent=None, ip_address=None)
    _, token_b, _ = await service.login(email="ada@example.com", password="correct-horse-1", user_agent=None, ip_address=None)
    session_a = await service.validate_session(session_token=token_a)

    await service.change_password(
        user_id=user.id, current_password="correct-horse-1", new_password="brand-new-password-9", keep_session_id=session_a.id,
    )

    await service.validate_session(session_token=token_a)
    with pytest.raises(SessionInvalidError):
        await service.validate_session(session_token=token_b)


# -- forgot password / reset ----------------------------------------------------


@pytest.mark.asyncio
async def test_forgot_password_sends_no_email_for_an_unregistered_address(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)

    await service.forgot_password(email="nobody@example.com")

    assert sender.sent == []


@pytest.mark.asyncio
async def test_forgot_password_sends_an_email_for_a_registered_address(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)
    await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    sender.sent.clear()  # discard the registration's own verification email

    await service.forgot_password(email="ada@example.com")

    assert len(sender.sent) == 1
    assert "reset" in sender.sent[0].subject.lower()


@pytest.mark.asyncio
async def test_reset_password_with_a_valid_token_changes_the_password(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)
    await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    sender.sent.clear()
    await service.forgot_password(email="ada@example.com")
    token = _extract_token(sender.sent[0].body)

    await service.reset_password(token=token, new_password="reset-password-42")

    await service.login(email="ada@example.com", password="reset-password-42", user_agent=None, ip_address=None)


@pytest.mark.asyncio
async def test_reset_password_token_is_single_use(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)
    await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    sender.sent.clear()
    await service.forgot_password(email="ada@example.com")
    token = _extract_token(sender.sent[0].body)
    await service.reset_password(token=token, new_password="reset-password-42")

    with pytest.raises(TokenInvalidError):
        await service.reset_password(token=token, new_password="another-password-99")


@pytest.mark.asyncio
async def test_reset_password_rejects_an_expired_token(tmp_path: Path) -> None:
    """A token created with an already-past `expires_at` -- the same shape a
    real one takes once its TTL elapses -- is refused, never redeemed.
    """

    tokens = InMemoryIdentityTokenStore()
    users = InMemoryUserStore()
    service = make_service(tmp_path, users=users, tokens=tokens)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    raw_token = generate_token()
    await tokens.create(
        user_id=user.id, token_hash=hash_token(raw_token), purpose=TokenPurpose.PASSWORD_RESET,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    with pytest.raises(TokenInvalidError):
        await service.reset_password(token=raw_token, new_password="reset-password-42")


@pytest.mark.asyncio
async def test_reset_password_rejects_a_garbage_token(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    with pytest.raises(TokenInvalidError):
        await service.reset_password(token="not-a-real-token", new_password="reset-password-42")


@pytest.mark.asyncio
async def test_a_second_reset_request_invalidates_the_first_tokens_link(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)
    await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    sender.sent.clear()
    await service.forgot_password(email="ada@example.com")
    first_token = _extract_token(sender.sent[0].body)
    await service.forgot_password(email="ada@example.com")

    with pytest.raises(TokenInvalidError):
        await service.reset_password(token=first_token, new_password="reset-password-42")


# -- email verification ---------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_email_verification_marks_the_account_verified(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)
    await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    token = _extract_token(sender.sent[0].body)

    await service.confirm_email_verification(token=token)

    stored = await service._users.get_by_email("ada@example.com")
    assert stored is not None and stored.email_verified is True


@pytest.mark.asyncio
async def test_resend_verification_is_a_no_op_once_already_verified(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    token = _extract_token(sender.sent[0].body)
    await service.confirm_email_verification(token=token)
    verified_user = await service._users.get_by_id(user.id)
    sender.sent.clear()

    sent = await service.resend_email_verification(user=verified_user)

    assert sent is False
    assert sender.sent == []


@pytest.mark.asyncio
async def test_a_password_reset_token_cannot_confirm_email_verification(tmp_path: Path) -> None:
    """Purpose-bound: a token minted for one purpose cannot be redeemed for the other."""

    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)
    await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    sender.sent.clear()
    await service.forgot_password(email="ada@example.com")
    reset_token = _extract_token(sender.sent[0].body)

    with pytest.raises(TokenInvalidError):
        await service.confirm_email_verification(token=reset_token)


def _extract_token(body: str) -> str:
    line = next(line for line in body.splitlines() if "token=" in line)
    return line.rsplit("token=", 1)[-1].strip()


# -- profile settings ---------------------------------------------------------


@pytest.mark.asyncio
async def test_update_profile_applies_only_the_fields_supplied(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")

    updated = await service.update_profile(user_id=user.id, preferred_timezone="America/New_York")

    assert updated.preferred_timezone == "America/New_York"
    assert updated.display_name == "Ada"  # untouched
    assert updated.preferred_locale == "en-US"  # untouched, still the default


@pytest.mark.asyncio
async def test_set_profile_image_records_the_artifact_and_its_workspace(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    workspace_id = uuid4()
    artifact_id = uuid4()

    updated = await service.set_profile_image(user_id=user.id, artifact_id=artifact_id, workspace_id=workspace_id)

    assert updated.profile_image_artifact_id == artifact_id
    assert updated.profile_image_workspace_id == workspace_id


# -- email change ------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_email_change_requires_the_correct_current_password(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")

    with pytest.raises(InvalidCredentialsError):
        await service.request_email_change(user_id=user.id, new_email="ada2@example.com", current_password="wrong")


@pytest.mark.asyncio
async def test_request_email_change_rejects_the_current_address(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")

    with pytest.raises(SameEmailError):
        await service.request_email_change(user_id=user.id, new_email="Ada@Example.com", current_password="correct-horse-1")


@pytest.mark.asyncio
async def test_request_email_change_rejects_an_address_already_registered(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    await service.register(email="grace@example.com", password="correct-horse-2", display_name="Grace")

    with pytest.raises(EmailAlreadyRegisteredError):
        await service.request_email_change(user_id=user.id, new_email="grace@example.com", current_password="correct-horse-1")


@pytest.mark.asyncio
async def test_request_email_change_sends_the_confirmation_to_the_new_address_only(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    sender.sent.clear()

    await service.request_email_change(user_id=user.id, new_email="ada-new@example.com", current_password="correct-horse-1")

    assert len(sender.sent) == 1
    assert sender.sent[0].to == "ada-new@example.com"


@pytest.mark.asyncio
async def test_confirm_email_change_applies_the_pending_address_and_verifies_it(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    await service.request_email_change(user_id=user.id, new_email="ada-new@example.com", current_password="correct-horse-1")
    token = _extract_token(sender.sent[-1].body)

    updated = await service.confirm_email_change(token=token)

    assert updated.email == "ada-new@example.com"
    assert updated.pending_email is None
    assert updated.email_verified is True


@pytest.mark.asyncio
async def test_confirm_email_change_revokes_every_session(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    _, token, _ = await service.login(email="ada@example.com", password="correct-horse-1", user_agent=None, ip_address=None)
    session = await service.validate_session(session_token=token)
    await service.request_email_change(user_id=user.id, new_email="ada-new@example.com", current_password="correct-horse-1")
    change_token = _extract_token(sender.sent[-1].body)

    await service.confirm_email_change(token=change_token)

    with pytest.raises(SessionInvalidError):
        await service.validate_session(session_token=token)
    assert session.id  # the pre-change session existed and is now the one revoked


@pytest.mark.asyncio
async def test_confirm_email_change_token_is_single_use(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    await service.request_email_change(user_id=user.id, new_email="ada-new@example.com", current_password="correct-horse-1")
    token = _extract_token(sender.sent[-1].body)
    await service.confirm_email_change(token=token)

    with pytest.raises(TokenInvalidError):
        await service.confirm_email_change(token=token)


@pytest.mark.asyncio
async def test_a_second_email_change_request_invalidates_the_first_tokens_link(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    await service.request_email_change(user_id=user.id, new_email="ada-first@example.com", current_password="correct-horse-1")
    first_token = _extract_token(sender.sent[-1].body)
    await service.request_email_change(user_id=user.id, new_email="ada-second@example.com", current_password="correct-horse-1")

    with pytest.raises(TokenInvalidError):
        await service.confirm_email_change(token=first_token)


# -- audit log -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_password_change_is_recorded_in_the_audit_log(tmp_path: Path) -> None:
    audit = InMemoryAuditLogStore()
    service = make_service(tmp_path, audit=audit)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    _, token, _ = await service.login(email="ada@example.com", password="correct-horse-1", user_agent=None, ip_address=None)
    session = await service.validate_session(session_token=token)

    await service.change_password(
        user_id=user.id, current_password="correct-horse-1", new_password="brand-new-password-9", keep_session_id=session.id,
    )

    entries = await audit.list_for_user(user_id=user.id)
    assert [entry.event_type for entry in entries] == ["identity_password_changed"]
    assert entries[0].workspace_id is None


@pytest.mark.asyncio
async def test_email_change_request_and_confirm_are_both_recorded_in_the_audit_log(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    audit = InMemoryAuditLogStore()
    service = make_service(tmp_path, email_sender=sender, audit=audit)
    user = await service.register(email="ada@example.com", password="correct-horse-1", display_name="Ada")
    await service.request_email_change(user_id=user.id, new_email="ada-new@example.com", current_password="correct-horse-1")
    token = _extract_token(sender.sent[-1].body)

    await service.confirm_email_change(token=token)

    entries = await audit.list_for_user(user_id=user.id)
    event_types = [entry.event_type for entry in entries]
    assert "identity_email_change_requested" in event_types
    assert "identity_email_change_confirmed" in event_types
