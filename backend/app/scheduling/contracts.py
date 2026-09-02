"""A recurring instruction to run a saved report on a deterministic clock.

A schedule names *when*, never *what to say*: scheduled execution always goes
through ``SavedReportExecutionService``, the same deterministic
semantic-metric pipeline a manual run uses, and therefore never reaches an
LLM. See ``app.scheduling.calculator`` for exactly how ``next_run_at`` is
computed from a ``ScheduleConfig``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.analytics.presentation.templates import DocumentFormat
from app.delivery.contracts import DeliveryChannel

ScheduleKind = Literal["daily", "weekly", "monthly", "quarterly"]

#: What a schedule's last attempt produced. Distinct from an execution's own
#: ``ExecutionStatus`` ("running"/"completed"/"failed") -- "skipped" exists
#: only at the schedule level, for a due row whose saved report turned out to
#: be missing or archived, where no execution ever started.
ScheduleResult = Literal["completed", "failed", "skipped"]


class ScheduleConfig(BaseModel):
    """A deterministic recurrence rule, in the schedule's own local clock.

    ``day_of_month`` is deliberately capped at 28 -- the one day every
    calendar month has, February included -- rather than accepting 29-31 and
    then having to decide whether a schedule silently shifts, clamps, or skips
    in a short month. A reader who wants "the last day of the month" is not
    served by this shape; that is a deliberate scope limit, not an oversight.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ScheduleKind
    hour: int = Field(default=6, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)
    #: Only for kind="weekly". Monday=0 .. Sunday=6, matching ``date.weekday()``.
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    #: Only for kind="monthly" or "quarterly".
    day_of_month: int | None = Field(default=None, ge=1, le=28)
    #: Only for kind="quarterly": which month of each 3-month cycle this runs
    #: in. 1 -> Jan/Apr/Jul/Oct, 2 -> Feb/May/Aug/Nov, 3 -> Mar/Jun/Sep/Dec.
    month_of_quarter: int | None = Field(default=None, ge=1, le=3)

    @model_validator(mode="after")
    def _shape_matches_kind(self) -> ScheduleConfig:
        if self.kind == "weekly":
            if self.day_of_week is None:
                raise ValueError("weekly requires 'day_of_week'.")
        elif self.day_of_week is not None:
            raise ValueError(f"'day_of_week' is only meaningful for weekly, not {self.kind!r}.")

        if self.kind in ("monthly", "quarterly"):
            if self.day_of_month is None:
                raise ValueError(f"{self.kind} requires 'day_of_month'.")
        elif self.day_of_month is not None:
            raise ValueError(f"'day_of_month' is only meaningful for monthly/quarterly, not {self.kind!r}.")

        if self.kind == "quarterly":
            if self.month_of_quarter is None:
                raise ValueError("quarterly requires 'month_of_quarter'.")
        elif self.month_of_quarter is not None:
            raise ValueError(f"'month_of_quarter' is only meaningful for quarterly, not {self.kind!r}.")
        return self


def _validated_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError(f"Unknown IANA timezone: {value!r}.") from error
    return value


class ScheduledReportDefinition(BaseModel):
    """The durable schedule: when a saved report should run, and where it goes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    saved_report_id: UUID
    workspace_id: str = Field(min_length=1, max_length=128)
    schedule: ScheduleConfig
    timezone: str = Field(min_length=1, max_length=64)
    formats: list[DocumentFormat] = Field(min_length=1, max_length=2)
    delivery_channel: DeliveryChannel | None = None
    delivery_destination: str | None = Field(default=None, max_length=2_000)
    enabled: bool
    next_run_at: datetime
    last_run_at: datetime | None = None
    last_result: ScheduleResult | None = None
    consecutive_failures: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime

    @field_validator("timezone")
    @classmethod
    def _timezone_is_known(cls, value: str) -> str:
        return _validated_timezone(value)

    @model_validator(mode="after")
    def _delivery_needs_a_destination(self) -> ScheduledReportDefinition:
        if (self.delivery_channel is None) != (self.delivery_destination is None):
            raise ValueError("delivery_channel and delivery_destination must be set together.")
        return self
