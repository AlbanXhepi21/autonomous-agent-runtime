"""The public view of a run.

These are produced by the run manager and serialised unchanged by the API, so
they live beside what builds them rather than in the HTTP layer that forwards
them. Keeping them here is what lets orchestration stay independent of app.api.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.presentation.charts import ChartSpec

RunStatusLiteral = Literal["running", "completed", "failed", "waiting_for_approval"]


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
    status: RunStatusLiteral
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    metrics: RunMetricsResponse | None = None
    charts: list[ChartSpec] = Field(default_factory=list)


class RunResponse(BaseModel):
    run_id: str
    conversation_id: str
    status: RunStatusLiteral
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
