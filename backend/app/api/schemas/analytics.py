"""Stable, frontend-facing contracts for the Data Analyst Workbench."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.presentation.document_model import NarrativeStatus
from app.analytics.presentation.preview import ReportPreview, TemplateSuitabilityOverview
from app.analytics.semantics.parameters import MetricParameters
from app.contracts.answers import AnswerSource
from app.orchestration.views import (
    PublicRunEvent,
    PublicRunEventListResponse,
    RunHistoryResponse,
    RunMetricsResponse,
    RunResponse,
)

# Re-exported so route modules name one source for request and response shapes.
__all__ = [
    "AnswerSource", "ConversationCreateRequest", "MetricParameters", "MetricSummaryResponse",
    "MetricListResponse", "NarrativeStatus", "PublishReportRequest", "PublishReportResponse",
    "PublishedDocumentResponse", "ReportPreview", "ReportPreviewRequest", "ReportTemplateListResponse",
    "ReportTemplateResponse", "ConversationDetailResponse", "ConversationListResponse",
    "ConversationResponse", "ConversationTitleRequest", "CreateRunRequest",
    "CreateRunResponse", "MessageResponse", "PublicRunEvent",
    "PublicRunEventListResponse", "RunHistoryResponse", "RunMetricsResponse", "RunResponse",
    "TemplateSuitabilityOverview",
]


class CreateRunRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=200)


class CreateRunResponse(BaseModel):
    run_id: str
    conversation_id: str
    status: Literal["running"]


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=255)


class ConversationTitleRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class MessageResponse(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    run_id: str | None = None


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int
    limit: int
    offset: int


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse]
    messages_total: int
    messages_limit: int
    messages_offset: int
    runs: list["RunHistoryResponse"] = Field(default_factory=list)


class ReportTemplateResponse(BaseModel):
    """One publishable document shape offered to the Workbench."""

    name: str
    title: str
    description: str
    report_type: str
    period_granularity: str
    sections: list[str]


class ReportTemplateListResponse(BaseModel):
    items: list[ReportTemplateResponse]


class PublishReportRequest(BaseModel):
    """What a caller may choose when publishing. Never what a report says.

    Rejecting unknown fields rather than ignoring them is the point: a request
    carrying a figure would otherwise look accepted, and a caller could believe
    it had put a number into a report. Every value in a published document comes
    from a query the run executed.
    """

    model_config = ConfigDict(extra="forbid")

    template: str = Field(min_length=1, max_length=64)
    formats: list[Literal["pdf", "docx"]] = Field(min_length=1, max_length=2)
    #: Free text, because the runtime cannot know what period an analysis
    #: covered; it is printed only when the caller supplies it.
    period: str | None = Field(default=None, max_length=120)
    title: str | None = Field(default=None, max_length=120)
    #: Sections to recompute from their metric definitions. Each names a metric,
    #: a period, groupings and filters — never a value, a column or a fragment
    #: of SQL. Absent means publish the run exactly as it was answered.
    metrics: list[MetricParameters] = Field(default_factory=list, max_length=8)
    #: What to do with the run's prose when the figures were recomputed.
    #: Defaults to leaving it out, which is the only option that cannot mislead.
    narrative: NarrativeStatus | None = None


class ReportPreviewRequest(BaseModel):
    """What a caller may choose to preview. The same shape ``publish`` takes,
    minus the output formats a preview never renders — never a figure.
    """

    model_config = ConfigDict(extra="forbid")

    template: str = Field(min_length=1, max_length=64)
    period: str | None = Field(default=None, max_length=120)
    title: str | None = Field(default=None, max_length=120)
    metrics: list[MetricParameters] = Field(default_factory=list, max_length=8)
    narrative: NarrativeStatus | None = None


class MetricSummaryResponse(BaseModel):
    """One metric a reader may recompute, and what it will accept.

    Only ever built from a metric whose lifecycle status is beyond
    "documented" -- see ``MetricRegistry.list_rerunnable`` -- so
    ``lifecycle_status`` here is always one a reader may actually execute;
    a documentation-only metric never reaches this response.
    """

    name: str
    display_name: str
    description: str
    unit: str
    format: str
    dimensions: list[str]
    filters: list[str]
    grains: list[str]
    value_columns: list[str]
    required_tables: list[str]
    caveats: list[str]
    lifecycle_status: str


class MetricListResponse(BaseModel):
    items: list[MetricSummaryResponse]


class PublishedDocumentResponse(BaseModel):
    artifact_id: str
    name: str
    media_type: str
    size: int


class PublishReportResponse(BaseModel):
    run_id: str
    template: str
    documents: list[PublishedDocumentResponse]
    #: What became of the run's prose. Reported so a caller cannot believe the
    #: narrative was refreshed when it was pinned or dropped.
    narrative: NarrativeStatus = "current"
    #: Evidence identifiers minted by this publish, when figures were recomputed.
    rerun_query_ids: list[str] = Field(default_factory=list)
