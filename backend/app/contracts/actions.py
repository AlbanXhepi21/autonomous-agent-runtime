"""Structured actions produced by an LLM."""

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ActionType = Literal["use_tool", "load_skill", "delegate", "delegate_parallel", "finish"]

#: A published report prints these as its stated limitations, so the list has to
#: stay short enough to read and each entry short enough to be a sentence.
MAX_CAVEATS = 10
MAX_CAVEAT_LENGTH = 500

_COLLAPSE_WHITESPACE = re.compile(r"\s+")


def normalize_caveats(values: Any) -> list[str]:
    """Reduce model-supplied caveats to the bounded list a report may print.

    Total by design. A finish action arrives after the analysis is already
    done, and rejecting it would throw that work away over a caveat that ran
    long or was repeated — so anything that does not fit the bounds is dropped
    here rather than raised. What survives is stripped, non-blank, within
    length, and free of duplicates that differ only in case or spacing.
    """

    if not isinstance(values, list):
        return []
    accepted: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        caveat = value.strip()
        # Truncating prose mid-sentence would publish a misleading fragment, so
        # an over-long caveat is omitted rather than cut down.
        if not caveat or len(caveat) > MAX_CAVEAT_LENGTH:
            continue
        fingerprint = _COLLAPSE_WHITESPACE.sub(" ", caveat).casefold()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        accepted.append(caveat)
        if len(accepted) == MAX_CAVEATS:
            break
    return accepted


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
    citations: list[str] = Field(
        default_factory=list,
        max_length=12,
        description=(
            "Stable evidence identifiers the final answer rests on. References only; "
            "the runtime resolves each one against what the run executed."
        ),
    )
    caveats: list[str] = Field(
        default_factory=list,
        description=(
            "Genuine limitations of this analysis, printed as the report's stated "
            "limitations. Normalized to at most "
            f"{MAX_CAVEATS} unique entries of {MAX_CAVEAT_LENGTH} characters."
        ),
    )

    @field_validator("caveats", mode="before")
    @classmethod
    def bound_caveats(cls, values: Any) -> list[str]:
        """Hold only caveats a report may print, whatever the model supplied."""

        return normalize_caveats(values)

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
        if self.action_type != "finish" and self.citations:
            raise ValueError("only finish actions may carry citations")
        if self.action_type != "finish" and self.caveats:
            raise ValueError("only finish actions may carry caveats")
        return self
