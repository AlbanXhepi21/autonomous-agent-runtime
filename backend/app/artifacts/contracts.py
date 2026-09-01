"""Typed, metadata-only descriptions of user-consumable agent artifacts."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ArtifactStatus(StrEnum):
    """Where an artifact is in the write-then-record sequence.

    A record is created before its bytes are in place and only becomes
    ``READY`` once they are verified, so a crash between the two leaves a
    ``PENDING`` row that retrieval refuses rather than a successful-looking
    record pointing at a partial file.
    """

    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


class Artifact(BaseModel):
    """A registered file output, deliberately separate from observations and memory."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    #: Provider-independent location, relative to the artifact area. Never an
    #: absolute path: the same key must resolve on another machine, and later
    #: against object storage rather than a workspace directory.
    relative_path: str = Field(min_length=1, max_length=512)
    artifact_type: str = Field(min_length=1, max_length=64)
    media_type: str = Field(min_length=1, max_length=128)
    size: int = Field(ge=0)
    #: Hex SHA-256 of the stored bytes, so a download can be checked against
    #: what was recorded.
    sha256: str = Field(min_length=64, max_length=64)
    status: ArtifactStatus = ArtifactStatus.READY
    run_id: str = Field(min_length=1, max_length=128)
    created_at: datetime
    #: Set only for documents published from a report template.
    output_format: str | None = Field(default=None, max_length=16)
    template_id: str | None = Field(default=None, max_length=64)
    template_version: str | None = Field(default=None, max_length=32)
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
