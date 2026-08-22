"""Typed contracts for deterministic agent-runtime evaluations."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.observability import RunMetrics, SystemRunMetrics


class EvalCase(BaseModel):
    """One readable set of outcome constraints for an agent run."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    description: str = Field(min_length=1, max_length=2_000)
    goal: str = Field(min_length=1, max_length=4_000)
    setup: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    expected_stop_reason: str | None = None
    expected_capabilities: list[str] = Field(default_factory=list)
    forbidden_capabilities: list[str] = Field(default_factory=list)
    expected_skills: list[str] = Field(default_factory=list)
    expected_delegation: bool | None = None
    expected_artifact: bool | None = None
    expected_security_decisions: list[str] = Field(default_factory=list)
    trajectory: "TrajectoryExpectation" = Field(default_factory=lambda: TrajectoryExpectation())
    custom_success_criteria: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "name", "description", "goal")
    @classmethod
    def require_non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class EvalDataset(BaseModel):
    """A named suite loaded from one JSON dataset file."""

    model_config = ConfigDict(extra="forbid")

    suite: str = Field(min_length=1, max_length=64)
    cases: list[EvalCase] = Field(min_length=1)

    @field_validator("cases")
    @classmethod
    def require_unique_case_ids(cls, cases: list[EvalCase]) -> list[EvalCase]:
        ids = [case.id for case in cases]
        if len(ids) != len(set(ids)):
            raise ValueError("case IDs must be unique within a suite")
        return cases


class EvaluatorResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluator: str
    passed: bool
    reason: str | None = None


class TrajectoryExpectation(BaseModel):
    """Optional observable behavior constraints; none infer task semantics."""

    model_config = ConfigDict(extra="forbid")

    max_iterations: int | None = Field(default=None, ge=0)
    max_tool_calls: int | None = Field(default=None, ge=0)
    max_delegations: int | None = Field(default=None, ge=0)
    required_action_types: list[str] = Field(default_factory=list)
    forbidden_action_types: list[str] = Field(default_factory=list)
    max_duplicate_actions: int | None = Field(default=None, ge=0)
    expect_failure_recovery: bool | None = None
    max_actions_after_finish: int | None = Field(default=None, ge=0)
    max_denied_actions_per_capability: int | None = Field(default=None, ge=1)


class EvalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    suite: str
    passed: bool
    score: float = Field(ge=0, le=1)
    failure_reasons: list[str] = Field(default_factory=list)
    run_id: str | None = None
    duration_ms: int = Field(ge=0)
    stop_reason: str | None = None
    trace_run_id: str | None = None
    evaluator_results: list[EvaluatorResult] = Field(default_factory=list)
    trajectory_score: float | None = Field(default=None, ge=0, le=1)
    trajectory_diagnostics: list[str] = Field(default_factory=list)
    metrics: RunMetrics | None = None
    system_metrics: SystemRunMetrics | None = None


class SuiteReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suite: str
    results: list[EvalResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(result.passed for result in self.results)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def average(self, field: str) -> float | None:
        values = [getattr(result.metrics, field) for result in self.results if result.metrics and getattr(result.metrics, field) is not None]
        return sum(values) / len(values) if values else None
