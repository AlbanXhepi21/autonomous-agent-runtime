"""Authentication and account-lifecycle behavior over identity storage.

Everything HTTP-shaped -- cookies, status codes, request bodies -- lives in
``app.api``; this module only knows about users, sessions, and tokens.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.audit.store import AuditLogStore, InMemoryAuditLogStore
from app.core.logging import log_event
from app.identity.contracts import IdentityToken, Session, TokenPurpose, User
from app.identity.email import EmailMessage, EmailSender
from app.identity.passwords import PasswordHasher
from app.identity.rate_limit import RateLimiter
from app.identity.store import IdentityTokenStore, SessionStore, UserStore
from app.identity.tokens import generate_token, hash_token

_logger = logging.getLogger(__name__)

#: Matches the client-visible constraint enforced again in app.api.schemas.auth;
#: kept here too so the service is safe to call directly, not only through HTTP.
MIN_PASSWORD_LENGTH = 8

# A syntactically valid Argon2id hash that no real password will ever match.
# Verifying against it when no account exists spends roughly the same time a
# real verification would, so a failed login costs about the same whether or
# not the email is registered.
_DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$MDAwMDAwMDAwMDAwMDAwMA$"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
)


class IdentityError(Exception):
    """Base class for identity-domain failures the API layer must translate."""


class EmailAlreadyRegisteredError(IdentityError):
    pass


class WeakPasswordError(IdentityError):
    pass


class InvalidCredentialsError(IdentityError):
    pass


class AccountDisabledError(IdentityError):
    pass


class SessionInvalidError(IdentityError):
    pass


class TokenInvalidError(IdentityError):
    pass


class SameEmailError(IdentityError):
    """Raised when a requested email change targets the account's current address."""


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _now() -> datetime:
    return datetime.now(UTC)


def _truncate(value: str | None, limit: int = 255) -> str | None:
    return None if value is None else value[:limit]


class AuthService:
    def __init__(
        self, *, users: UserStore, sessions: SessionStore, tokens: IdentityTokenStore,
        password_hasher: PasswordHasher, email_sender: EmailSender, rate_limiter: RateLimiter,
        session_idle_ttl_seconds: int, session_absolute_ttl_seconds: int,
        password_reset_ttl_seconds: int, email_verification_ttl_seconds: int, app_base_url: str,
        audit: AuditLogStore | None = None,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._tokens = tokens
        self._passwords = password_hasher
        self._email = email_sender
        self._rate_limiter = rate_limiter
        self._session_idle_ttl = timedelta(seconds=session_idle_ttl_seconds)
        self._session_absolute_ttl = timedelta(seconds=session_absolute_ttl_seconds)
        self._password_reset_ttl = timedelta(seconds=password_reset_ttl_seconds)
        self._email_verification_ttl = timedelta(seconds=email_verification_ttl_seconds)
        self._app_base_url = app_base_url.rstrip("/")
        # Defaults to a process-local store rather than making every existing
        # AuthService construction site (many, across the test suite) supply
        # one just to keep working -- the same optional-collaborator pattern
        # ``ReportPublisher.reruns`` already uses.
        self._audit = audit or InMemoryAuditLogStore()

    @property
    def rate_limiter(self) -> RateLimiter:
        return self._rate_limiter

    @property
    def session_absolute_ttl_seconds(self) -> int:
        return int(self._session_absolute_ttl.total_seconds())

    # -- registration ------------------------------------------------------

    async def register(self, *, email: str, password: str, display_name: str) -> User:
        normalized = normalize_email(email)
        if len(password) < MIN_PASSWORD_LENGTH:
            raise WeakPasswordError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        if await self._users.get_by_email(normalized) is not None:
            raise EmailAlreadyRegisteredError(normalized)
        password_hash = self._passwords.hash(password)
        user = await self._users.create(email=normalized, display_name=display_name.strip(), password_hash=password_hash)
        log_event(_logger, logging.INFO, "identity_user_registered", user_id=str(user.id), email=user.email)
        await self._issue_and_send_token(user, purpose=TokenPurpose.EMAIL_VERIFICATION)
        return user

    # -- login / session lifecycle ------------------------------------------

    async def login(
        self, *, email: str, password: str, user_agent: str | None, ip_address: str | None,
    ) -> tuple[User, str, str]:
        """Return ``(user, session_token, csrf_token)``. Both tokens are shown to the caller exactly once."""

        normalized = normalize_email(email)
        user = await self._users.get_by_email(normalized)
        if user is None:
            self._passwords.verify(password_hash=_DUMMY_PASSWORD_HASH, password=password)
            log_event(_logger, logging.INFO, "identity_login_failed", email=normalized, reason="no_such_user")
            raise InvalidCredentialsError("Invalid email or password.")
        if not self._passwords.verify(password_hash=user.password_hash, password=password):
            log_event(_logger, logging.INFO, "identity_login_failed", user_id=str(user.id), reason="bad_password")
            raise InvalidCredentialsError("Invalid email or password.")
        if self._passwords.needs_rehash(user.password_hash):
            await self._users.update_password_hash(user.id, self._passwords.hash(password))
        if not user.is_active:
            log_event(_logger, logging.INFO, "identity_login_rejected", user_id=str(user.id), reason="disabled")
            raise AccountDisabledError("This account has been disabled.")

        session_token, csrf_token = generate_token(), generate_token()
        now = _now()
        session = await self._sessions.create(
            user_id=user.id, token_hash=hash_token(session_token), csrf_token_hash=hash_token(csrf_token),
            expires_at=now + self._session_absolute_ttl,
            user_agent=_truncate(user_agent), ip_address=_truncate(ip_address),
        )
        await self._users.record_login(user.id, at=now)
        log_event(_logger, logging.INFO, "identity_login_succeeded", user_id=str(user.id), session_id=str(session.id))
        return user.model_copy(update={"last_login_at": now}), session_token, csrf_token

    async def validate_session(self, *, session_token: str) -> Session:
        """Resolve a live session from its cookie value and refresh its idle timer.

        Raises ``SessionInvalidError`` uniformly for "no such session",
        "revoked", "past its absolute lifetime", and "idle too long" -- a
        caller only ever needs to know the session is no longer usable, never
        which of those it was.
        """

        session = await self._sessions.get_by_token_hash(hash_token(session_token))
        now = _now()
        if session is None or session.revoked_at is not None:
            raise SessionInvalidError("Session not found or revoked.")
        if now > session.expires_at:
            raise SessionInvalidError("Session exceeded its absolute lifetime.")
        if now - session.last_seen_at > self._session_idle_ttl:
            raise SessionInvalidError("Session expired from inactivity.")
        await self._sessions.touch(session.id, last_seen_at=now)
        return session.model_copy(update={"last_seen_at": now})

    async def user_for_session(self, session: Session) -> User:
        user = await self._users.get_by_id(session.user_id)
        if user is None or not user.is_active:
            raise AccountDisabledError("This account is no longer active.")
        return user

    async def logout(self, *, session_id: UUID) -> None:
        await self._sessions.revoke(session_id)
        log_event(_logger, logging.INFO, "identity_session_revoked", session_id=str(session_id))

    async def logout_all(self, *, user_id: UUID) -> int:
        count = await self._sessions.revoke_all_for_user(user_id)
        log_event(_logger, logging.INFO, "identity_all_sessions_revoked", user_id=str(user_id), count=count)
        return count

    # -- password management -------------------------------------------------

    async def change_password(
        self, *, user_id: UUID, current_password: str, new_password: str, keep_session_id: UUID,
    ) -> None:
        user = await self._users.get_by_id(user_id)
        if user is None or not self._passwords.verify(password_hash=user.password_hash, password=current_password):
            raise InvalidCredentialsError("Current password is incorrect.")
        if len(new_password) < MIN_PASSWORD_LENGTH:
            raise WeakPasswordError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        await self._users.update_password_hash(user_id, self._passwords.hash(new_password))
        await self._sessions.revoke_all_for_user(user_id, except_session_id=keep_session_id)
        log_event(_logger, logging.INFO, "identity_password_changed", user_id=str(user_id))
        await self._audit.record(actor_user_id=user_id, workspace_id=None, event_type="identity_password_changed")

    async def forgot_password(self, *, email: str) -> None:
        """Complete identically whether or not the address is registered.

        The caller-facing response is the same either way (see
        ``app.api.routes.auth.forgot_password``); this method's own job is
        only to decide, server-side, whether an email actually goes out.
        """

        normalized = normalize_email(email)
        user = await self._users.get_by_email(normalized)
        if user is None or not user.is_active:
            log_event(
                _logger, logging.INFO, "identity_password_reset_requested",
                email=normalized, outcome="no_such_active_account",
            )
            return
        await self._issue_and_send_token(user, purpose=TokenPurpose.PASSWORD_RESET)
        log_event(_logger, logging.INFO, "identity_password_reset_requested", user_id=str(user.id), outcome="sent")

    async def reset_password(self, *, token: str, new_password: str) -> None:
        record = await self._consume_token(token, purpose=TokenPurpose.PASSWORD_RESET)
        if len(new_password) < MIN_PASSWORD_LENGTH:
            raise WeakPasswordError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        await self._users.update_password_hash(record.user_id, self._passwords.hash(new_password))
        await self._sessions.revoke_all_for_user(record.user_id)
        log_event(_logger, logging.INFO, "identity_password_reset_completed", user_id=str(record.user_id))

    # -- email verification ---------------------------------------------------

    async def resend_email_verification(self, *, user: User) -> bool:
        """Return ``False`` without sending anything when already verified."""

        if user.email_verified:
            return False
        await self._issue_and_send_token(user, purpose=TokenPurpose.EMAIL_VERIFICATION)
        return True

    async def confirm_email_verification(self, *, token: str) -> None:
        record = await self._consume_token(token, purpose=TokenPurpose.EMAIL_VERIFICATION)
        await self._users.mark_email_verified(record.user_id)
        log_event(_logger, logging.INFO, "identity_email_verified", user_id=str(record.user_id))

    # -- profile settings ----------------------------------------------------

    async def update_profile(
        self, *, user_id: UUID, display_name: str | None = None,
        preferred_timezone: str | None = None, preferred_locale: str | None = None,
    ) -> User:
        updated = await self._users.update_profile(
            user_id, display_name=display_name, preferred_timezone=preferred_timezone,
            preferred_locale=preferred_locale,
        )
        if updated is None:
            raise InvalidCredentialsError("Account no longer exists.")
        log_event(_logger, logging.INFO, "identity_profile_updated", user_id=str(user_id))
        return updated

    async def set_profile_image(
        self, *, user_id: UUID, artifact_id: UUID | None, workspace_id: UUID | None,
    ) -> User:
        """``artifact_id``/``workspace_id`` must already be a registered artifact in that
        workspace's store -- this call only records the pointer, never touches artifact storage.
        """

        updated = await self._users.set_profile_image(user_id, artifact_id=artifact_id, workspace_id=workspace_id)
        if updated is None:
            raise InvalidCredentialsError("Account no longer exists.")
        log_event(_logger, logging.INFO, "identity_profile_image_set", user_id=str(user_id), artifact_id=str(artifact_id) if artifact_id else None)
        return updated

    # -- email change ----------------------------------------------------------

    async def request_email_change(self, *, user_id: UUID, new_email: str, current_password: str) -> None:
        """Password-reauthenticated, like ``change_password``. The confirmation
        token is sent to the *new* address only -- reaching it is what proves
        the caller actually controls it, the same property email verification
        at registration already relies on.
        """

        user = await self._users.get_by_id(user_id)
        if user is None or not self._passwords.verify(password_hash=user.password_hash, password=current_password):
            raise InvalidCredentialsError("Current password is incorrect.")
        normalized = normalize_email(new_email)
        if normalized == user.email:
            raise SameEmailError("The new email must differ from the current one.")
        if await self._users.get_by_email(normalized) is not None:
            raise EmailAlreadyRegisteredError(normalized)

        await self._users.set_pending_email(user_id, pending_email=normalized)
        await self._tokens.revoke_active_for_user(user_id, purpose=TokenPurpose.EMAIL_CHANGE)
        raw_token = generate_token()
        await self._tokens.create(
            user_id=user_id, token_hash=hash_token(raw_token), purpose=TokenPurpose.EMAIL_CHANGE,
            expires_at=_now() + self._email_verification_ttl,
        )
        link = f"{self._app_base_url}/confirm-email-change?token={raw_token}"
        await self._email.send(EmailMessage(
            to=normalized, subject="Confirm your new email address",
            body=(
                f"Confirm that {normalized} should replace {user.email} as your sign-in email.\n\n"
                f"{link}\n\n"
                "If you did not request this, you can safely ignore this email -- your address will not change."
            ),
        ))
        log_event(_logger, logging.INFO, "identity_email_change_requested", user_id=str(user_id))
        await self._audit.record(
            actor_user_id=user_id, workspace_id=None, event_type="identity_email_change_requested",
            metadata={"new_email": normalized},
        )

    async def confirm_email_change(self, *, token: str) -> User:
        record = await self._consume_token(token, purpose=TokenPurpose.EMAIL_CHANGE)
        user = await self._users.get_by_id(record.user_id)
        if user is None or user.pending_email is None:
            raise TokenInvalidError("This link is invalid or has expired.")
        if await self._users.get_by_email(user.pending_email) is not None:
            raise EmailAlreadyRegisteredError(user.pending_email)

        updated = await self._users.apply_email_change(record.user_id, new_email=user.pending_email)
        assert updated is not None
        # A changed sign-in email is as security-sensitive as a changed
        # password: every other session stops trusting the old address.
        await self._sessions.revoke_all_for_user(record.user_id)
        log_event(_logger, logging.INFO, "identity_email_change_confirmed", user_id=str(record.user_id))
        await self._audit.record(
            actor_user_id=record.user_id, workspace_id=None, event_type="identity_email_change_confirmed",
            metadata={"new_email": updated.email},
        )
        return updated

    # -- shared token plumbing ---------------------------------------------

    async def _issue_and_send_token(self, user: User, *, purpose: TokenPurpose) -> None:
        # At most one live token per (user, purpose): a fresh request supersedes
        # rather than accumulates, so an old, still-unexpired email link a user
        # forgot about can't be redeemed after a newer one was requested.
        await self._tokens.revoke_active_for_user(user.id, purpose=purpose)
        raw_token = generate_token()
        ttl = self._password_reset_ttl if purpose is TokenPurpose.PASSWORD_RESET else self._email_verification_ttl
        await self._tokens.create(user_id=user.id, token_hash=hash_token(raw_token), purpose=purpose, expires_at=_now() + ttl)
        await self._email.send(self._compose_message(user, purpose=purpose, raw_token=raw_token))

    def _compose_message(self, user: User, *, purpose: TokenPurpose, raw_token: str) -> EmailMessage:
        if purpose is TokenPurpose.PASSWORD_RESET:
            link = f"{self._app_base_url}/reset-password?token={raw_token}"
            return EmailMessage(
                to=user.email, subject="Reset your password",
                body=(
                    "We received a request to reset your password.\n\n"
                    f"{link}\n\n"
                    "If you did not request this, you can safely ignore this email."
                ),
            )
        link = f"{self._app_base_url}/verify-email?token={raw_token}"
        return EmailMessage(
            to=user.email, subject="Verify your email",
            body=f"Confirm your email address to finish setting up your account.\n\n{link}",
        )

    async def _consume_token(self, raw_token: str, *, purpose: TokenPurpose) -> IdentityToken:
        record = await self._tokens.get_by_token_hash(hash_token(raw_token), purpose=purpose)
        now = _now()
        if record is None or record.used_at is not None or record.revoked_at is not None or record.expires_at < now:
            raise TokenInvalidError("This link is invalid or has expired.")
        await self._tokens.mark_used(record.id, at=now)
        return record
