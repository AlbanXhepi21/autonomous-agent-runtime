"""Runtime state models for an agent task."""

from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field

from app.agent.delegation import (
    DelegationObservation,
    DelegationRequest,
    ParallelDelegationResult,
    SubagentResult,
)
from app.tools.models import ToolResult
from app.artifacts.models import Artifact


class Observation(BaseModel):
    """A result the agent can consider in a later iteration."""

    source: str
    content: ToolResult | DelegationObservation | SubagentResult | ParallelDelegationResult
    iteration: int = Field(ge=1)
    sequence: int = Field(ge=1)


class TaskSummary(BaseModel):
    """Compact, current understanding of progress in one agent run."""

    goal: str
    progress: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    important_decisions: list[str] = Field(default_factory=list)
    failures_or_blockers: list[str] = Field(default_factory=list)
    last_updated_iteration: int = Field(default=0, ge=0)
    summarized_observation_count: int = Field(default=0, ge=0)


class StopReason(StrEnum):
    """Why an agent run reached its terminal state."""

    COMPLETED = "completed"
    MAX_ITERATIONS = "max_iterations"
    MAX_TOOL_CALLS = "max_tool_calls"
    TOO_MANY_ERRORS = "too_many_errors"
    CANCELLED = "cancelled"
    FATAL_ERROR = "fatal_error"


class AgentState(BaseModel):
    """All mutable state belonging to one bounded agent run."""

    goal: str
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    observations: list[Observation] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    task_summary: TaskSummary | None = None
    loaded_skills: dict[str, str] = Field(default_factory=dict)
    delegation_requests: list[DelegationRequest] = Field(default_factory=list)
    successful_delegation_count: int = 0
    failed_delegation_count: int = 0
    child_run_ids: list[str] = Field(default_factory=list)
    parallel_delegation_batch_count: int = 0
    recent_delegation_fingerprints: list[str] = Field(default_factory=list)
    agent_depth: int = Field(default=0, ge=0)
    iteration_count: int = 0
    total_tool_calls: int = 0
    recoverable_error_count: int = 0
    recent_action_fingerprints: list[str] = Field(default_factory=list)
    completed: bool = False
    final_answer: str | None = None
    stop_reason: StopReason | None = None
