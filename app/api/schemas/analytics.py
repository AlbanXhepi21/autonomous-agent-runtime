"""Stable, frontend-facing contracts for the Data Analyst Workbench."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from app.analytics.charts import ChartSpec


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


class RunMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    iterations: int = 0
    tool_calls: int = 0
    delegations: int = 0
    total_duration_ms: int | None = None
    database_query_count: int = 0
    database_rows_returned: int = 0
    database_rejected_query_count: int = 0
    total_tokens: int | None = None
    estimated_cost: float | None = None


class RunHistoryResponse(BaseModel):
    run_id: str
    status: Literal["running", "completed", "failed", "waiting_for_approval"]
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    metrics: RunMetricsResponse | None = None
    charts: list[ChartSpec] = Field(default_factory=list)


class RunResponse(BaseModel):
    run_id: str
    conversation_id: str
    status: Literal["running", "completed", "failed", "waiting_for_approval"]
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    final_response: str | None = None
    error: str | None = None
    metrics: RunMetricsResponse | None = None
    charts: list[ChartSpec] = Field(default_factory=list)


class PublicRunEvent(BaseModel):
    """A deliberately small event envelope; never a serialized runtime object."""

    id: str
    run_id: str
    type: str
    timestamp: datetime
    data: dict[str, Any] = Field(default_factory=dict)


class PublicRunEventListResponse(BaseModel):
    items: list[PublicRunEvent]
