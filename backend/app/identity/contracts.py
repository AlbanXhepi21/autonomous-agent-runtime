"""Identity domain types: users, sessions, and recovery/verification tokens.

A leaf module in the same spirit as ``app.contracts`` -- no store, no
password-hashing library, no FastAPI. Everything here is a plain, frozen
description of state; behavior lives in ``app.identity.service``.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TokenPurpose(StrEnum):
    """What a recovery/verification token may be redeemed for -- and nothing else."""

    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"
    #: Redeeming this applies ``User.pending_email`` -- the token proves the
    #: caller can receive mail at the new address, it never carries the
    #: address itself (see ``AuthService.request_email_change``).
    EMAIL_CHANGE = "email_change"


class User(BaseModel):
    """A registered account. ``password_hash`` never leaves this layer --
    every API response is built from ``app.api.schemas.auth.UserResponse``,
    which has no field for it.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID
    email: str
    display_name: str
    password_hash: str
    is_active: bool
    email_verified: bool
    #: Set while an email change is awaiting confirmation at the new
    #: address; cleared (applied to ``email``) or abandoned on confirm.
    pending_email: str | None = None
    preferred_timezone: str = "UTC"
    preferred_locale: str = "en-US"
    #: Both set together or both ``None`` -- an artifact has no meaning
    #: without knowing which workspace's store it lives in (see
    #: ``AuthService.set_profile_image``).
    profile_image_artifact_id: UUID | None = None
    profile_image_workspace_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None


class Session(BaseModel):
    """A server-side session behind an HTTP-only cookie.

    ``token_hash``/``csrf_token_hash`` are the only forms either secret takes
    once persisted; the raw values exist only in the two cookies issued to
    the browser at login.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID
    user_id: UUID
    token_hash: str
    csrf_token_hash: str
    created_at: datetime
    expires_at: datetime
    last_seen_at: datetime
    revoked_at: datetime | None = None
    user_agent: str | None = None
    ip_address: str | None = None


class IdentityToken(BaseModel):
    """A single-use, purpose-bound password-reset or email-verification token."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    user_id: UUID
    token_hash: str
    purpose: TokenPurpose
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None = None
    revoked_at: datetime | None = None
