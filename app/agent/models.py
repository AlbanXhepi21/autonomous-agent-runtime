"""Structured actions produced by an LLM."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ActionType = Literal["use_tool", "load_skill", "finish"]


class AgentAction(BaseModel):
    """One operational decision made by the agent."""

    action_type: ActionType
    reasoning_summary: str = Field(
        description="A short operational explanation, not private reasoning."
    )
    tool_name: str | None = None
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    skill_name: str | None = None
    final_answer: str | None = None

    @model_validator(mode="after")
    def validate_action_payload(self) -> "AgentAction":
        """Require the payload appropriate for each action type."""

        if self.action_type == "use_tool" and not self.tool_name:
            raise ValueError("use_tool actions require tool_name")
        if self.action_type == "load_skill" and not self.skill_name:
            raise ValueError("load_skill actions require skill_name")
        if self.action_type == "finish" and not self.final_answer:
            raise ValueError("finish actions require final_answer")
        return self
