"""Lightweight, evidence-linked contracts for analytical conclusions."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnalyticalFinding(BaseModel):
    """One observation or interpretation tied to one or more executed queries."""

    model_config = ConfigDict(extra="forbid")
    statement: str = Field(min_length=1, max_length=2_000)
    metric: str | None = Field(default=None, max_length=128)
    value: Any | None = None
    comparison: str | None = Field(default=None, max_length=1_000)
    time_period: str | None = Field(default=None, max_length=256)
    dimensions: dict[str, str] = Field(default_factory=dict)
    evidence_query_ids: list[str] = Field(default_factory=list)
    confidence_note: str | None = Field(default=None, max_length=1_000)
