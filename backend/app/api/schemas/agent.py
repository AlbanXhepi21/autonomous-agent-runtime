"""Schemas for the agent HTTP interface."""

from pydantic import BaseModel, Field

from app.artifacts.contracts import Artifact
from app.runtime.state import RunStatus, StopReason


class AgentRunRequest(BaseModel):
    """A user goal submitted to the agent runtime.

    Carries no ``workspace_id`` -- a client-supplied identifier is never
    authorization. The caller's tenant is resolved server-side from the
    authenticated session and the ``workspace_id`` query parameter (see
    ``app.api.dependencies.require_permission``), the same as every other
    tenant-scoped route.
    """

    goal: str = Field(min_length=1)
    session_id: str | None = None


class ToolOutcomeSummary(BaseModel):
    """Safe execution information useful when reviewing an agent run."""

    tool_name: str
    success: bool
    error: str | None = None
    blocked_as_duplicate: bool = False


class AgentRunResponse(BaseModel):
    """The current result of an agent run."""

    final_answer: str | None
    run_id: str
    iteration_count: int
    tool_call_count: int
    recoverable_error_count: int
    duplicate_action_count: int
    tools_used: list[str]
    tool_outcomes: list[ToolOutcomeSummary]
    skills_used: list[str]
    completed: bool
    status: RunStatus
    stop_reason: StopReason | None
    artifacts: list[Artifact] = Field(default_factory=list)
