"""Stable, frontend-facing contracts for durable saved report definitions."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.analytics.presentation.preview import ReportPreview
from app.analytics.semantics.parameters import Grain, MetricFilter
from app.reports.contracts import (
    ExecutionMode,
    ExecutionStatus,
    NarrativePolicy,
    RelativePeriodKind,
    SavedReportStatus,
)

#: Used whenever a caller does not name a workspace. This application has no
#: workspace/tenant table of its own yet -- every saved-report query is still
#: filtered by this identifier, so isolation is real and enforced, not merely
#: assumed for a system that happens to serve one workspace today.
DEFAULT_WORKSPACE_ID = "default"


class MetricRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric: str = Field(min_length=1, max_length=64)
    dimensions: list[str] = Field(default_factory=list, max_length=3)
    filters: list[MetricFilter] = Field(default_factory=list, max_length=8)
    grain: Grain = "month"


class RelativePeriodPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: RelativePeriodKind
    days: int | None = Field(default=None, ge=1)
    start: date | None = None
    end: date | None = None


class SavedReportCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(default=DEFAULT_WORKSPACE_ID, min_length=1, max_length=128)
    owner: str | None = Field(default=None, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2_000)
    template_id: str = Field(min_length=1, max_length=64)
    metric_requests: list[MetricRequestPayload] = Field(min_length=1, max_length=24)
    default_period: RelativePeriodPayload
    narrative_policy: NarrativePolicy = "exclude"
    #: Captured once from the run a reader was viewing when they saved this
    #: definition -- never fetched again later, so a definition survives that
    #: run or its conversation being deleted.
    seed_run_id: str | None = Field(default=None, max_length=255)
    seed_narrative: str | None = Field(default=None, max_length=20_000)
    seed_narrative_period: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def _include_original_needs_a_seed(self) -> SavedReportCreateRequest:
        if self.narrative_policy == "include_original" and not self.seed_narrative:
            raise ValueError(
                "narrative_policy 'include_original' requires seed_narrative, captured from the "
                "run being saved."
            )
        return self


class SavedReportUpdateRequest(BaseModel):
    """A partial update. Only the fields present are changed.

    ``expected_version`` enforces optimistic concurrency: it must equal the
    definition's current stored version, or the update is refused with a
    conflict rather than silently overwriting a concurrent edit.
    """

    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2_000)
    template_id: str | None = Field(default=None, min_length=1, max_length=64)
    metric_requests: list[MetricRequestPayload] | None = Field(default=None, min_length=1, max_length=24)
    default_period: RelativePeriodPayload | None = None
    narrative_policy: NarrativePolicy | None = None
    seed_run_id: str | None = Field(default=None, max_length=255)
    seed_narrative: str | None = Field(default=None, max_length=20_000)
    seed_narrative_period: str | None = Field(default=None, max_length=160)
    status: SavedReportStatus | None = None


class SavedReportArchiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)


class SavedReportSummaryResponse(BaseModel):
    """One row of a saved-report list -- no narrative text, for a light payload."""

    id: str
    workspace_id: str
    owner: str | None
    name: str
    description: str | None
    template_id: str
    template_version: str
    narrative_policy: NarrativePolicy
    status: SavedReportStatus
    version: int
    created_at: datetime
    updated_at: datetime


class SavedReportResponse(SavedReportSummaryResponse):
    """The full definition, including what a rerun will actually request."""

    metric_requests: list[MetricRequestPayload]
    default_period: RelativePeriodPayload
    seed_run_id: str | None
    seed_narrative: str | None
    seed_narrative_period: str | None


class SavedReportListResponse(BaseModel):
    items: list[SavedReportSummaryResponse]
    total: int
    limit: int
    offset: int


class ResolvedParametersResponse(BaseModel):
    """What executing this definition right now would actually use.

    Produced without running a single query -- steps 1-3 of execution only,
    read-only against nothing but the template registry and the clock.
    """

    resolved_period_start: date
    resolved_period_end: date
    resolved_period_description: str
    metric_requests: list[MetricRequestPayload]
    pinned_template_version: str
    current_template_version: str
    template_version_matches_pin: bool


class SavedReportExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["preview", "publish"] = "preview"
    formats: list[Literal["pdf", "docx"]] = Field(default_factory=lambda: ["pdf"], max_length=2)


class PublishedDocumentSummary(BaseModel):
    artifact_id: str
    name: str
    media_type: str
    size: int


class SavedReportExecuteResponse(BaseModel):
    execution_id: str
    run_id: str
    mode: ExecutionMode
    status: ExecutionStatus
    resolved_period_start: date
    resolved_period_end: date
    preview: ReportPreview | None = None
    documents: list[PublishedDocumentSummary] = Field(default_factory=list)


class SavedReportExecutionResponse(BaseModel):
    id: str
    run_id: str
    mode: ExecutionMode
    status: ExecutionStatus
    resolved_period_start: date | None
    resolved_period_end: date | None
    formats: list[str] | None
    error: str | None
    created_at: datetime
    completed_at: datetime | None
    artifacts: list[PublishedDocumentSummary] = Field(default_factory=list)


class SavedReportExecutionListResponse(BaseModel):
    items: list[SavedReportExecutionResponse]
    total: int
    limit: int
    offset: int
