"""Sanitized, typed execution-trace contracts."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.core.logging import safe_log_value


class TraceEventType(StrEnum):
    RUN_STARTED = "run_started"
    RUN_FINISHED = "run_finished"
    RUN_FAILED = "run_failed"
    LLM_REQUEST_STARTED = "llm_request_started"
    LLM_REQUEST_FINISHED = "llm_request_finished"
    LLM_REQUEST_FAILED = "llm_request_failed"
    TOOL_STARTED = "tool_started"
    TOOL_FINISHED = "tool_finished"
    TOOL_FAILED = "tool_failed"
    SKILL_LOADED = "skill_loaded"
    MEMORY_RETRIEVAL_STARTED = "memory_retrieval_started"
    MEMORY_RETRIEVAL_FINISHED = "memory_retrieval_finished"
    TASK_SUMMARY_STARTED = "task_summary_started"
    TASK_SUMMARY_FINISHED = "task_summary_finished"
    DELEGATION_STARTED = "delegation_started"
    DELEGATION_FINISHED = "delegation_finished"
    PARALLEL_DELEGATION_STARTED = "parallel_delegation_started"
    PARALLEL_DELEGATION_FINISHED = "parallel_delegation_finished"
    SECURITY_POLICY_EVALUATED = "security_policy_evaluated"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RESOLVED = "approval_resolved"
    ARTIFACT_CREATED = "artifact_created"
    OPERATION_FAILED = "operation_failed"
    RETRY_SCHEDULED = "retry_scheduled"
    RETRY_STARTED = "retry_started"
    RETRY_SUCCEEDED = "retry_succeeded"
    RETRY_EXHAUSTED = "retry_exhausted"
    DATABASE_SCHEMA_LISTED = "database_schema_listed"
    DATABASE_TABLE_DESCRIBED = "database_table_described"
    DATABASE_RELATIONSHIPS_INSPECTED = "database_relationships_inspected"
    DATABASE_SCHEMA_SEARCHED = "database_schema_searched"
    DATABASE_QUERY_VALIDATION_STARTED = "database_query_validation_started"
    DATABASE_QUERY_VALIDATED = "database_query_validated"
    DATABASE_QUERY_REJECTED = "database_query_rejected"
    DATABASE_QUERY_STARTED = "database_query_started"
    DATABASE_QUERY_FINISHED = "database_query_finished"
    DATABASE_QUERY_FAILED = "database_query_failed"
    ANALYTICS_PYTHON_STARTED = "analytics_python_started"
    ANALYTICS_PYTHON_FINISHED = "analytics_python_finished"
    ANALYTICS_PYTHON_FAILED = "analytics_python_failed"
    CHART_CREATED = "chart_created"
    REPORT_CREATED = "report_created"


class TraceStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_FOR_APPROVAL = "waiting_for_approval"


def sanitize_trace_metadata(metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Keep trace metadata bounded and free of reasoning or credential material."""

    forbidden = ("reasoning", "chain_of_thought", "cot", "prompt", "credential", "secret")
    def sanitize(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: sanitize(item)
                for key, item in value.items()
                if not any(part in str(key).lower() for part in forbidden)
            }
        if isinstance(value, list | tuple):
            return [sanitize(item) for item in value]
        return safe_log_value(value)

    return sanitize(metadata or {})


class TraceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    parent_run_id: str | None = None
    child_run_id: str | None = None
    event_type: TraceEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    iteration: int | None = Field(default=None, ge=0)
    span_id: str | None = None
    parent_span_id: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    status: TraceStatus | None = None
    success: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    span_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    parent_span_id: str | None = None
    name: str
    event_type: TraceEventType
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    status: TraceStatus = TraceStatus.RUNNING
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunMetrics(BaseModel):
    """Derived run-local performance and economic summary from trace events."""

    model_config = ConfigDict(extra="forbid")

    iterations: int = 0
    llm_calls: int = 0
    tool_calls: int = 0
    delegations: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost: float | None = None
    llm_duration_ms: int = 0
    tool_duration_ms: int = 0
    memory_duration_ms: int = 0
    summary_duration_ms: int = 0
    delegation_duration_ms: int = 0
    database_query_count: int = 0
    database_query_duration_ms: int = 0
    database_rows_returned: int = 0
    database_rejected_query_count: int = 0
    database_timeout_count: int = 0
    total_duration_ms: int | None = None


class RunTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    parent_run_id: str | None = None
    agent_name: str
    agent_type: str
    goal: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    status: TraceStatus = TraceStatus.RUNNING
    stop_reason: str | None = None
    events: list[TraceEvent] = Field(default_factory=list)
    spans: list[TraceSpan] = Field(default_factory=list)
    metrics: RunMetrics = Field(default_factory=RunMetrics)
