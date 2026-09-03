"""Request and response models for workspace, membership, report-preference,
and audit-log endpoints.

Every request model is ``extra="forbid"``: an unrecognized field is a client
bug (a stale integration, a typo) worth surfacing as a 422, not silently
dropped.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validation import validate_bcp47_locale, validate_iana_timezone, validate_iso4217_currency
from app.tenancy.contracts import MembershipStatus, ReportNarrativePolicyDefault, Role

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")


def _validate_email(value: str) -> str:
    stripped = value.strip()
    if not _EMAIL_PATTERN.match(stripped):
        raise ValueError("Enter a valid email address.")
    return stripped


def _validate_slug(value: str) -> str:
    normalized = value.strip().lower()
    if not _SLUG_PATTERN.match(normalized):
        raise ValueError("Slug must be lowercase alphanumeric with single hyphens, 1-64 characters.")
    return normalized


class WorkspaceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=64)
    logo_ref: str | None = Field(default=None, max_length=2048)
    default_timezone: str = Field(default="UTC", max_length=64)
    default_locale: str = Field(default="en-US", max_length=16)
    default_currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str) -> str:
        return _validate_slug(value)

    @field_validator("default_timezone")
    @classmethod
    def _timezone(cls, value: str) -> str:
        return validate_iana_timezone(value)

    @field_validator("default_locale")
    @classmethod
    def _locale(cls, value: str) -> str:
        return validate_bcp47_locale(value)

    @field_validator("default_currency")
    @classmethod
    def _currency(cls, value: str) -> str:
        return validate_iso4217_currency(value)


class WorkspaceUpdateRequest(BaseModel):
    """Partial edit -- only fields the caller sets are applied.

    ``expected_version`` is required: this is the optimistic-concurrency
    token from the last ``WorkspaceResponse`` the caller read (see
    ``app.tenancy.store.WorkspaceVersionConflictError``), the same pattern
    ``app.api.schemas.saved_reports`` already establishes.
    """

    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    logo_ref: str | None = Field(default=None, max_length=2048)
    default_timezone: str | None = Field(default=None, max_length=64)
    default_locale: str | None = Field(default=None, max_length=16)
    default_currency: str | None = Field(default=None, min_length=3, max_length=3)
    fiscal_year_start_month: int | None = Field(default=None, ge=1, le=12)
    number_format: str | None = Field(default=None, min_length=1, max_length=32)
    date_format: str | None = Field(default=None, min_length=1, max_length=32)

    @field_validator("default_timezone")
    @classmethod
    def _timezone(cls, value: str | None) -> str | None:
        return None if value is None else validate_iana_timezone(value)

    @field_validator("default_locale")
    @classmethod
    def _locale(cls, value: str | None) -> str | None:
        return None if value is None else validate_bcp47_locale(value)

    @field_validator("default_currency")
    @classmethod
    def _currency(cls, value: str | None) -> str | None:
        return None if value is None else validate_iso4217_currency(value)


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    logo_ref: str | None
    is_active: bool
    default_timezone: str
    default_locale: str
    default_currency: str
    fiscal_year_start_month: int
    number_format: str
    date_format: str
    version: int
    created_at: datetime
    updated_at: datetime


class WorkspaceListResponse(BaseModel):
    items: list[WorkspaceResponse]


class MembershipResponse(BaseModel):
    id: UUID
    user_id: UUID
    workspace_id: UUID
    role: Role
    status: MembershipStatus
    invited_by: UUID | None
    joined_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MembershipListResponse(BaseModel):
    items: list[MembershipResponse]


class InviteMemberRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)
    role: Role

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return _validate_email(value)


class InvitationResponse(BaseModel):
    """Never gains a token field -- see app.tenancy.contracts.Invitation."""

    id: UUID
    workspace_id: UUID
    email: str
    role: Role
    invited_by: UUID | None
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None


class AcceptInvitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1)


class ChangeRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Role


class TransferOwnershipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to_user_id: UUID


# -- report preferences ------------------------------------------------------


class ReportPreferencesUpdateRequest(BaseModel):
    """Partial edit -- only fields the caller sets are applied.

    Every field here changes presentation only: which template, format,
    theme, or narrative a publish request falls back to when it doesn't say
    -- never a fact the report states.
    """

    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
    default_template: str | None = Field(default=None, max_length=128)
    default_output_format: Literal["pdf", "docx"] | None = None
    default_theme: str | None = Field(default=None, max_length=128)
    default_narrative_policy: ReportNarrativePolicyDefault | None = None
    evidence_appendix_enabled: bool | None = None
    technical_sql_appendix_enabled: bool | None = None


class ReportPreferencesResponse(BaseModel):
    workspace_id: UUID
    default_template: str | None
    default_output_format: Literal["pdf", "docx"] | None
    default_theme: str | None
    default_narrative_policy: ReportNarrativePolicyDefault | None
    evidence_appendix_enabled: bool
    technical_sql_appendix_enabled: bool
    version: int
    created_at: datetime
    updated_at: datetime


# -- audit log ----------------------------------------------------------------


class AuditLogEntryResponse(BaseModel):
    id: UUID
    actor_user_id: UUID | None
    workspace_id: UUID | None
    event_type: str
    metadata: dict
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogEntryResponse]
