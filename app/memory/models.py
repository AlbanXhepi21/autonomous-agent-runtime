"""Typed models for agent memories."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MemoryType(StrEnum):
    """The domain role a memory plays for the agent."""

    WORKING = "working"
    EPISODIC = "episodic"
    LONG_TERM = "long_term"


class Memory(BaseModel):
    """A validated piece of agent memory independent of its storage backend."""

    id: UUID = Field(default_factory=uuid4)
    memory_type: MemoryType
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    run_id: str | None = None
    session_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
