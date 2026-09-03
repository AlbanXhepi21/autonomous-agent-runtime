"""Audit-log domain types: an append-only record of security-relevant changes.

A leaf module in the same spirit as ``app.identity.contracts`` -- no store,
no FastAPI. An entry is either workspace-scoped (a tenant-settings or
membership change), user-scoped (a password or email change), or both (a
member's role changed within a workspace, by an actor who is that member) --
at least one of ``actor_user_id``/``workspace_id`` is always present, never
neither.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogEntry(BaseModel):
    """One immutable fact: who (if anyone known) did what, optionally to which workspace."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    #: The authenticated caller who triggered this change. ``None`` only for
    #: a small number of system-initiated events (there are none yet).
    actor_user_id: UUID | None
    #: The workspace this event concerns, if any -- absent for purely
    #: account-level events like a password or email change.
    workspace_id: UUID | None
    event_type: str
    #: Small, structured, and already safe to display -- never a secret,
    #: a password, or a raw token (the same discipline every ``log_event``
    #: call in this codebase already applies).
    metadata: dict[str, Any]
    created_at: datetime
