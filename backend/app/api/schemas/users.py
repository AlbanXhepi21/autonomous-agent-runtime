"""Request and response models for user profile/settings endpoints.

Every request model is ``extra="forbid"``. None of these responses ever gain
a ``password_hash`` field -- see ``app.identity.contracts.User`` -- and
``pending_email`` is deliberately the only hint a response gives that a
change is in flight; the token itself never round-trips through a response.
"""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validation import validate_bcp47_locale, validate_iana_timezone

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(value: str) -> str:
    stripped = value.strip()
    if not _EMAIL_PATTERN.match(stripped):
        raise ValueError("Enter a valid email address.")
    return stripped


class UserSettingsUpdateRequest(BaseModel):
    """Partial edit -- only fields the caller sets are applied."""

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    preferred_timezone: str | None = Field(default=None, max_length=64)
    preferred_locale: str | None = Field(default=None, max_length=16)

    @field_validator("preferred_timezone")
    @classmethod
    def _timezone(cls, value: str | None) -> str | None:
        return None if value is None else validate_iana_timezone(value)

    @field_validator("preferred_locale")
    @classmethod
    def _locale(cls, value: str | None) -> str | None:
        return None if value is None else validate_bcp47_locale(value)


class ProfileImageRequest(BaseModel):
    """The artifact must already exist in ``workspace_id``'s store -- this
    request only points the profile at it, it never uploads bytes itself
    (see ``app.api.routes.users.set_profile_image``, which registers the
    upload through the existing artifact system first).
    """

    model_config = ConfigDict(extra="forbid")

    artifact_id: UUID
    workspace_id: UUID


class RequestEmailChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_email: str = Field(min_length=3, max_length=320)
    current_password: str = Field(min_length=1, max_length=256)

    @field_validator("new_email")
    @classmethod
    def _email(cls, value: str) -> str:
        return _validate_email(value)


class ConfirmEmailChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1)


class UserSettingsResponse(BaseModel):
    """Never gains a password_hash field -- see app.identity.contracts.User."""

    id: UUID
    email: str
    pending_email: str | None
    display_name: str
    preferred_timezone: str
    preferred_locale: str
    profile_image_artifact_id: UUID | None
    profile_image_workspace_id: UUID | None
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None
