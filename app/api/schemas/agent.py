"""Schemas for the agent HTTP interface."""

from pydantic import BaseModel, Field

from app.agent.state import StopReason


class AgentRunRequest(BaseModel):
    """A user goal submitted to the agent runtime."""

    goal: str = Field(min_length=1)


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
    stop_reason: StopReason | None
