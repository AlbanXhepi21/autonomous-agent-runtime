"""Stable, frontend-facing contracts for scheduled saved-report execution."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.delivery.contracts import DeliveryChannel
from app.scheduling.contracts import ScheduleKind

DEFAULT_WORKSPACE_ID = "default"


class ScheduleConfigPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: ScheduleKind
    hour: int = Field(default=6, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    day_of_month: int | None = Field(default=None, ge=1, le=28)
    month_of_quarter: int | None = Field(default=None, ge=1, le=3)


class ScheduledReportCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(default=DEFAULT_WORKSPACE_ID, min_length=1, max_length=128)
    saved_report_id: UUID
    schedule: ScheduleConfigPayload
    timezone: str = Field(min_length=1, max_length=64)
    formats: list[Literal["pdf", "docx"]] = Field(default_factory=lambda: ["pdf"], max_length=2)
    delivery_channel: DeliveryChannel | None = None
    delivery_destination: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def _delivery_needs_a_destination(self) -> ScheduledReportCreateRequest:
        if (self.delivery_channel is None) != (self.delivery_destination is None):
            raise ValueError("delivery_channel and delivery_destination must be set together.")
        return self


class ScheduledReportUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule: ScheduleConfigPayload | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    formats: list[Literal["pdf", "docx"]] | None = Field(default=None, max_length=2)
    delivery_channel: DeliveryChannel | None = None
    delivery_destination: str | None = Field(default=None, max_length=2_000)
    enabled: bool | None = None


class ScheduledReportResponse(BaseModel):
    id: str
    saved_report_id: str
    workspace_id: str
    schedule: ScheduleConfigPayload
    timezone: str
    formats: list[str]
    delivery_channel: str | None
    delivery_destination: str | None
    enabled: bool
    next_run_at: datetime
    last_run_at: datetime | None
    last_result: str | None
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime


class ScheduledReportListResponse(BaseModel):
    items: list[ScheduledReportResponse]
    total: int
    limit: int
    offset: int


class DeliveryTriggerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    artifact_id: str = Field(min_length=1, max_length=64)
    channel: DeliveryChannel
    destination: str = Field(min_length=1, max_length=2_000)


class DeliveryResponse(BaseModel):
    id: str
    artifact_id: str
    channel: str
    destination: str
    status: str
    attempt_count: int
    last_attempt_at: datetime | None
    provider_metadata: dict
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
