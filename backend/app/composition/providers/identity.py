"""User identity, sessions, and authentication."""

from pathlib import Path

from app.composition.lifecycle import provider
from app.composition.providers.audit import get_audit_log_store
from app.composition.providers.persistence import get_runtime_database
from app.composition.providers.settings import get_settings
from app.identity.email import EmailSender, FileEmailSender
from app.identity.passwords import Argon2PasswordHasher, PasswordHasher
from app.identity.rate_limit import InMemoryRateLimiter, RateLimiter
from app.identity.service import AuthService
from app.identity.store import (
    IdentityTokenStore,
    InMemoryIdentityTokenStore,
    InMemorySessionStore,
    InMemoryUserStore,
    SessionStore,
    UserStore,
)


@provider
def get_password_hasher() -> PasswordHasher:
    return Argon2PasswordHasher()


@provider
def get_user_store() -> UserStore:
    settings = get_settings()
    if settings.identity_backend == "in_memory":
        return InMemoryUserStore()
    from app.identity.store import PostgresUserStore

    return PostgresUserStore(get_runtime_database())


@provider
def get_session_store() -> SessionStore:
    settings = get_settings()
    if settings.identity_backend == "in_memory":
        return InMemorySessionStore()
    from app.identity.store import PostgresSessionStore

    return PostgresSessionStore(get_runtime_database())


@provider
def get_identity_token_store() -> IdentityTokenStore:
    settings = get_settings()
    if settings.identity_backend == "in_memory":
        return InMemoryIdentityTokenStore()
    from app.identity.store import PostgresIdentityTokenStore

    return PostgresIdentityTokenStore(get_runtime_database())


@provider
def get_rate_limiter() -> RateLimiter:
    return InMemoryRateLimiter()


@provider
def get_email_sender() -> EmailSender:
    """No real mail provider exists yet; write to a local outbox instead.

    Rooted under the agent's own workspace so it is covered by the same
    ignored, ephemeral ``./var`` tree as everything else development writes
    to disk -- never through the structured logger, so a raw recovery link
    never reaches application logs.
    """

    settings = get_settings()
    return FileEmailSender(Path(settings.agent_workspace_root) / ".dev-mail")


@provider
def get_auth_service() -> AuthService:
    settings = get_settings()
    return AuthService(
        users=get_user_store(), sessions=get_session_store(), tokens=get_identity_token_store(),
        password_hasher=get_password_hasher(), email_sender=get_email_sender(), rate_limiter=get_rate_limiter(),
        session_idle_ttl_seconds=settings.session_idle_ttl_seconds,
        session_absolute_ttl_seconds=settings.session_absolute_ttl_seconds,
        password_reset_ttl_seconds=settings.reset_token_ttl_seconds,
        email_verification_ttl_seconds=settings.email_verification_token_ttl_seconds,
        app_base_url=settings.app_base_url, audit=get_audit_log_store(),
    )
