"""A typed investigation plan for complex analytical requests.

An `InvestigationPlan` is the agent's own bounded statement of what a request
requires: the questions an answer must resolve and the displays that should
carry the evidence. The model proposes and updates it through a tool call, the
same way any other typed capability works, so the loop stays "choose one next
action" rather than a fixed workflow.

Nothing here decides whether a plan is honoured. A question marked "answered"
or an output marked "created" is only the model's claim; `app.runtime.planning`
checks each claim against what the run actually produced before the runtime
treats it as true. This module holds only the shape of the claim.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RequestClass = Literal[
    "simple_fact", "comparison", "investigation", "executive_report", "detailed_report",
]

QuestionStatus = Literal["pending", "answered", "blocked"]
OutputStatus = Literal["pending", "created", "skipped", "blocked"]
OutputKind = Literal["kpi", "line", "bar", "stacked_bar", "area", "pie", "scatter", "table"]

#: Suggested (lower, upper) display counts per request class. Budgets, not
#: mandatory counts: nothing in this module or in enforcement requires a run
#: to reach the lower bound. The upper bound matches what `ChartSpecStore`
#: allows per run, so a plan can never promise more displays than a run could
#: actually create.
DISPLAY_BUDGETS: dict[RequestClass, tuple[int, int]] = {
    "simple_fact": (0, 1),
    "comparison": (1, 2),
    "investigation": (2, 4),
    "executive_report": (3, 6),
    "detailed_report": (5, 8),
}

MAX_QUESTIONS = 16
MAX_OUTPUTS = 16


class AnalysisQuestion(BaseModel):
    """One question the analysis must resolve, and what resolved it."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=40)
    question: str = Field(min_length=1, max_length=500)
    status: QuestionStatus = "pending"
    #: Stable `query_###` references the run produced. Only evidence the
    #: runtime can verify counts; see `app.runtime.planning.reconcile_plan`.
    evidence_ids: list[str] = Field(default_factory=list, max_length=12)


class PlannedOutput(BaseModel):
    """One display the plan calls for, and whether it exists yet."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=40)
    kind: OutputKind
    purpose: str = Field(min_length=1, max_length=300)
    required: bool = True
    status: OutputStatus = "pending"
    #: The `create_chart` display id this output resolved to, once created.
    display_id: str | None = Field(default=None, max_length=80)


class InvestigationPlan(BaseModel):
    """A bounded, typed statement of what one investigation requires.

    The plan is proposed and revised by the model through
    `update_investigation_plan`, then reconciled by the runtime against what
    the run actually produced. What survives reconciliation is what the
    runtime trusts when deciding whether `finish` may be accepted.
    """

    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=1, max_length=500)
    request_class: RequestClass
    questions: list[AnalysisQuestion] = Field(default_factory=list, max_length=MAX_QUESTIONS)
    outputs: list[PlannedOutput] = Field(default_factory=list, max_length=MAX_OUTPUTS)
    completion_criteria: list[str] = Field(default_factory=list, max_length=12)
    #: A ceiling the plan sets for itself, never a target. Capped at what a
    #: run can actually create.
    maximum_displays: int = Field(ge=0, le=8)

    @model_validator(mode="after")
    def _unique_ids(self) -> "InvestigationPlan":
        question_ids = [question.id for question in self.questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Analysis question ids must be unique within a plan.")
        output_ids = [output.id for output in self.outputs]
        if len(output_ids) != len(set(output_ids)):
            raise ValueError("Planned output ids must be unique within a plan.")
        return self

    @property
    def required_outputs(self) -> list[PlannedOutput]:
        return [output for output in self.outputs if output.required]
