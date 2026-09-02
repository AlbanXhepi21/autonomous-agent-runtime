"""A provider-neutral description of handing a ready artifact to its destination.

A delivery is never created for an artifact that isn't already verified and
``READY`` -- ``ArtifactStore.get`` itself refuses to return anything else, so
``DeliveryService`` enforces that guarantee simply by using ``get`` rather than
a raw record lookup. Nothing here ever carries a credential, a signed token,
or a raw provider response body: ``provider_metadata`` is sanitized before it
is ever attached to a record, by the provider that produced it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DeliveryChannel = Literal["link", "webhook", "email"]
DeliveryStatus = Literal["pending", "sent", "failed"]


class DeliveryRecord(BaseModel):
    """One attempt to deliver one artifact through one channel."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    artifact_id: str = Field(min_length=1, max_length=64)
    channel: DeliveryChannel
    #: A URL or an address an operator configured -- never a secret itself.
    destination: str = Field(min_length=1, max_length=2_000)
    status: DeliveryStatus
    attempt_count: int = Field(ge=0)
    last_attempt_at: datetime | None = None
    #: Sanitized by the provider that produced it: a status code, a truncated
    #: and redacted response snippet -- never a header, a token, or raw body.
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    failure_reason: str | None = Field(default=None, max_length=2_000)
    created_at: datetime
    updated_at: datetime


class DeliveryAttemptResult(BaseModel):
    """What one provider attempt produced, before it becomes a stored record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    success: bool
    #: Whether a failure is worth retrying (a timeout, a 5xx) as opposed to
    #: one that will never succeed on retry (an invalid destination, a 4xx).
    retryable: bool = False
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    failure_reason: str | None = Field(default=None, max_length=2_000)


class DeliveryError(Exception):
    """Raised when a delivery cannot be attempted at all -- not a provider failure."""
