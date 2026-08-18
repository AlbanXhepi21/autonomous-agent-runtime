"""Structured actions produced by an LLM."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ActionType = Literal["use_tool", "load_skill", "delegate", "delegate_parallel", "finish"]


class ParallelDelegationItem(BaseModel):
    """One bounded model-selected request within a parallel delegation action."""

    model_config = ConfigDict(extra="forbid")

    agent_name: str = Field(min_length=1)
    objective: str = Field(min_length=1, max_length=2_000)
    context: str | None = Field(default=None, max_length=2_000)
    constraints: str | None = Field(default=None, max_length=1_000)
    expected_output: str | None = Field(default=None, max_length=1_000)


class AgentAction(BaseModel):
    """One operational decision made by the agent."""

    action_type: ActionType
    reasoning_summary: str = Field(
        description="A short operational explanation, not private reasoning."
    )
    tool_name: str | None = None
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    skill_name: str | None = None
    agent_name: str | None = None
    objective: str | None = None
    context: str | None = None
    constraints: str | None = None
    expected_output: str | None = None
    delegations: list[ParallelDelegationItem] = Field(default_factory=list, max_length=8)
    final_answer: str | None = None

    @model_validator(mode="after")
    def validate_action_payload(self) -> "AgentAction":
        """Require the payload appropriate for each action type."""

        if self.action_type == "use_tool" and not self.tool_name:
            raise ValueError("use_tool actions require tool_name")
        if self.action_type == "load_skill" and not self.skill_name:
            raise ValueError("load_skill actions require skill_name")
        if self.action_type == "delegate":
            if not isinstance(self.agent_name, str) or not self.agent_name.strip():
                raise ValueError("delegate actions require agent_name")
            if not isinstance(self.objective, str) or not self.objective.strip():
                raise ValueError("delegate actions require a non-empty objective")
            if self.context is not None and not isinstance(self.context, str):
                raise ValueError("delegate action context must be a string when provided")
            if self.constraints is not None and not isinstance(self.constraints, str):
                raise ValueError("delegate action constraints must be a string when provided")
            if self.expected_output is not None and not isinstance(self.expected_output, str):
                raise ValueError("delegate action expected_output must be a string when provided")
        if self.action_type == "delegate_parallel" and len(self.delegations) < 2:
            raise ValueError("delegate_parallel actions require at least two delegations")
        if self.action_type == "finish" and not self.final_answer:
            raise ValueError("finish actions require final_answer")
        return self
