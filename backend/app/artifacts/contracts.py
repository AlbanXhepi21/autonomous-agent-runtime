"""Typed, metadata-only descriptions of user-consumable agent artifacts."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Artifact(BaseModel):
    """A registered file output, deliberately separate from observations and memory."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    relative_path: str = Field(min_length=1, max_length=512)
    artifact_type: str = Field(min_length=1, max_length=64)
    media_type: str = Field(min_length=1, max_length=128)
    size: int = Field(ge=0)
    run_id: str = Field(min_length=1, max_length=128)
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
