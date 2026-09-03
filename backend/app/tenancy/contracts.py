"""Tenancy domain types: workspaces, memberships, and invitations.

A leaf module in the same spirit as ``app.identity.contracts`` -- no store,
no FastAPI, no other ``app`` package. Everything here is a plain, frozen
description of state; behavior lives in ``app.tenancy.service``.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

#: Deliberately duplicated from ``app.core.validation`` (which
#: ``app.api.schemas.tenancy`` uses for the same checks at the request
#: boundary) rather than imported -- ``tests/contracts/test_tenancy_boundaries.py``
#: enforces that this module imports no other ``app`` package at all, the
#: same "leaf module" contract ``app.identity.contracts`` keeps.
_LOCALE_PATTERN = re.compile(r"^[a-z]{2,3}(-[A-Z][a-z]{3})?(-([A-Z]{2}|[0-9]{3}))?$")

_ISO_4217_CURRENCIES: frozenset[str] = frozenset({
    "AED", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AUD", "AWG", "AZN",
    "BAM", "BBD", "BDT", "BGN", "BHD", "BIF", "BMD", "BND", "BOB", "BOV",
    "BRL", "BSD", "BTN", "BWP", "BYN", "BZD", "CAD", "CDF", "CHE", "CHF",
    "CHW", "CLF", "CLP", "CNY", "COP", "COU", "CRC", "CUC", "CUP", "CVE",
    "CZK", "DJF", "DKK", "DOP", "DZD", "EGP", "ERN", "ETB", "EUR", "FJD",
    "FKP", "GBP", "GEL", "GHS", "GIP", "GMD", "GNF", "GTQ", "GYD", "HKD",
    "HNL", "HTG", "HUF", "IDR", "ILS", "INR", "IQD", "IRR", "ISK", "JMD",
    "JOD", "JPY", "KES", "KGS", "KHR", "KMF", "KPW", "KRW", "KWD", "KYD",
    "KZT", "LAK", "LBP", "LKR", "LRD", "LSL", "LYD", "MAD", "MDL", "MGA",
    "MKD", "MMK", "MNT", "MOP", "MRU", "MUR", "MVR", "MWK", "MXN", "MXV",
    "MYR", "MZN", "NAD", "NGN", "NIO", "NOK", "NPR", "NZD", "OMR", "PAB",
    "PEN", "PGK", "PHP", "PKR", "PLN", "PYG", "QAR", "RON", "RSD", "RUB",
    "RWF", "SAR", "SBD", "SCR", "SDG", "SEK", "SGD", "SHP", "SLE", "SOS",
    "SRD", "SSP", "STN", "SVC", "SYP", "SZL", "THB", "TJS", "TMT", "TND",
    "TOP", "TRY", "TTD", "TWD", "TZS", "UAH", "UGX", "USD", "USN", "UYI",
    "UYU", "UYW", "UZS", "VED", "VES", "VND", "VUV", "WST", "XAF", "XAG",
    "XAU", "XBA", "XBB", "XBC", "XBD", "XCD", "XDR", "XOF", "XPD", "XPF",
    "XPT", "XSU", "XTS", "XUA", "XXX", "YER", "ZAR", "ZMW", "ZWL",
})


def validate_iana_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError(f"Unknown IANA timezone: {value!r}.") from error
    return value


def validate_iso4217_currency(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in _ISO_4217_CURRENCIES:
        raise ValueError(f"Unknown ISO 4217 currency code: {value!r}.")
    return normalized


def validate_bcp47_locale(value: str) -> str:
    stripped = value.strip()
    if not _LOCALE_PATTERN.match(stripped):
        raise ValueError(f"Invalid locale tag: {value!r}. Expected a BCP-47 tag such as 'en-US'.")
    return stripped


class Role(StrEnum):
    """Ordered, in the sense that OWNER can manage everything ADMIN can and more.

    Nothing in this module encodes that ordering as comparable values --
    see ``app.tenancy.service`` for the specific "admins cannot manage
    owners" rule, kept in exactly one place.
    """

    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class Workspace(BaseModel):
    """A tenant organization -- the isolation boundary every tenant-owned
    resource's ``workspace_id`` foreign key ultimately points to.

    ``version`` backs optimistic-concurrency updates, the same pattern
    ``app.reports.contracts.SavedReportDefinition.version`` already
    establishes: a caller must supply the version it last read, and a
    concurrent edit in between is a conflict, not a silent overwrite.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID
    name: str
    slug: str
    logo_ref: str | None = None
    is_active: bool
    default_timezone: str
    default_locale: str
    default_currency: str
    #: 1-12; which calendar month a fiscal year begins in. 1 = January, i.e.
    #: the fiscal and calendar year coincide -- the common default.
    fiscal_year_start_month: int = Field(default=1, ge=1, le=12)
    #: A free-form token naming a display convention (e.g. "1,234.56" vs
    #: "1.234,56") -- presentation only, never reinterpreted as a parsing rule.
    number_format: str = "1,234.56"
    #: Same spirit as ``number_format``: a display token (e.g. "YYYY-MM-DD"),
    #: not a strptime/strftime pattern evaluated anywhere.
    date_format: str = "YYYY-MM-DD"
    version: int = Field(default=1, ge=1)
    created_at: datetime
    updated_at: datetime

    @field_validator("default_timezone")
    @classmethod
    def _timezone_is_known(cls, value: str) -> str:
        return validate_iana_timezone(value)

    @field_validator("default_locale")
    @classmethod
    def _locale_is_valid(cls, value: str) -> str:
        return validate_bcp47_locale(value)

    @field_validator("default_currency")
    @classmethod
    def _currency_is_known(cls, value: str) -> str:
        return validate_iso4217_currency(value)


#: Mirrors ``app.reports.contracts.NarrativePolicy`` -- kept as its own
#: literal rather than imported, since ``app.tenancy`` must not depend on
#: ``app.reports`` (a tenant-organization concept should not reach into a
#: business-resource package just to name a policy shape it merely echoes).
ReportNarrativePolicyDefault = Literal["exclude", "include_original", "require_new_investigation"]


class ReportPreferences(BaseModel):
    """A workspace's defaults for producing a report -- presentation choices
    a publish request may omit and fall back to, never a fact about the data.
    """

    model_config = ConfigDict(frozen=True)

    workspace_id: UUID
    default_template: str | None = Field(default=None, max_length=128)
    default_output_format: Literal["pdf", "docx"] | None = None
    default_theme: str | None = Field(default=None, max_length=128)
    default_narrative_policy: ReportNarrativePolicyDefault | None = None
    evidence_appendix_enabled: bool = True
    #: Stored for forward compatibility; no current renderer prints a SQL
    #: appendix, so this preference has no observable effect yet -- see
    #: ``docs/TENANCY.md``. It changes nothing about the facts a report states.
    technical_sql_appendix_enabled: bool = False
    version: int = Field(default=1, ge=1)
    created_at: datetime
    updated_at: datetime


class Membership(BaseModel):
    """One user's standing in one workspace. ``invited_by`` is ``None`` only
    for the membership a workspace's creator receives automatically.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID
    user_id: UUID
    workspace_id: UUID
    role: Role
    status: MembershipStatus
    invited_by: UUID | None = None
    joined_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class Invitation(BaseModel):
    """A pending offer to join a workspace at a given role.

    Bound to a normalized email address, not a user id -- the invitee may
    not have an account yet. ``token_hash`` mirrors
    ``app.identity.contracts.IdentityToken``: the raw token is never stored.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID
    workspace_id: UUID
    email: str
    role: Role
    token_hash: str
    invited_by: UUID | None = None
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None
