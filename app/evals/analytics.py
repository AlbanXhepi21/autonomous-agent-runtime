"""Evaluation-only contracts for Data Analyst benchmarks.

This module deliberately has no runtime imports.  In particular, ground truth is
loaded here by an explicit evaluator command and is never added to AgentState,
AgentContext, skills, memory, prompts, or analytics tools.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent.state import AgentState
from app.observability import RunTrace, TraceEventType


class GroundTruthScenario(BaseModel):
    """Private evaluator input, compatible with the data-generator scenario file."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    scenario_id: str
    name: str
    period: dict[str, str]
    root_cause: str
    affected_dimensions: dict[str, Any] = Field(default_factory=dict)
    expected_effects: list[str] = Field(default_factory=list)
    relevant_tables: list[str] = Field(default_factory=list)


class GroundTruthLoader:
    """Loads private benchmark input only when an evaluator explicitly asks for it."""

    @staticmethod
    def load(path: Path) -> dict[str, GroundTruthScenario]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("Ground-truth scenarios must be a JSON list.")
        scenarios = [GroundTruthScenario.model_validate(item) for item in payload]
        result = {scenario.scenario_id: scenario for scenario in scenarios}
        if len(result) != len(scenarios):
            raise ValueError("Ground-truth scenario IDs must be unique.")
        return result


class AnalyticsEvalCase(BaseModel):
    """A public question plus evaluator-only expectations.

    `ground_truth_id` is an opaque lookup key: the scenario contents remain in
    the loader and evaluator, never in the question sent to the analyst.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    suite: str
    question: str
    kind: str = "analysis"  # metric | root_cause | security | reporting
    ground_truth_id: str | None = None
    required_tables: list[str] = Field(default_factory=list)
    required_terms: list[str] = Field(default_factory=list)
    forbidden_terms: list[str] = Field(default_factory=list)
    required_artifacts: list[str] = Field(default_factory=list)
    max_queries: int | None = Field(default=None, ge=0)
    expect_python: bool | None = None
    expect_security_bypass_count: int = Field(default=0, ge=0)

    @field_validator("id", "suite", "question")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


class AnalyticsEvalDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cases: list[AnalyticsEvalCase] = Field(min_length=1)

    @field_validator("cases")
    @classmethod
    def unique_ids(cls, cases: list[AnalyticsEvalCase]) -> list[AnalyticsEvalCase]:
        if len({case.id for case in cases}) != len(cases):
            raise ValueError("Analytics eval case IDs must be unique.")
        return cases


def load_analytics_dataset(path: Path) -> AnalyticsEvalDataset:
    return AnalyticsEvalDataset.model_validate_json(path.read_text(encoding="utf-8"))


class AnalyticsCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    suite: str
    passed: bool
    score: float = Field(ge=0, le=1)
    checks: dict[str, bool]
    failures: list[str] = Field(default_factory=list)
    query_count: int = 0
    schema_inspections: int = 0
    duplicate_queries: int = 0
    failed_queries: int = 0
    rejected_queries: int = 0
    python_calls: int = 0
    delegations: int = 0
    iterations: int = 0
    tokens: int | None = None
    cost: float | None = None
    latency_ms: int | None = None


class SemanticEvaluator(Protocol):
    """Optional narrative judge. Never used by deterministic CI or security gates."""

    def evaluate(self, *, question: str, answer: str, ground_truth: GroundTruthScenario) -> float: ...


def _normalise(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").replace("-", " ").split())


class DeterministicAnalyticsEvaluator:
    """Scores observable evidence, trace behavior, and safe answer assertions."""

    def __init__(self, ground_truth: dict[str, GroundTruthScenario] | None = None) -> None:
        self._ground_truth = ground_truth or {}

    def evaluate(self, case: AnalyticsEvalCase, state: AgentState, trace: RunTrace | None) -> AnalyticsCaseResult:
        scenario = self._ground_truth.get(case.ground_truth_id or "")
        answer = _normalise(state.final_answer or "")
        events = trace.events if trace else []
        query_events = [event for event in events if event.event_type is TraceEventType.DATABASE_QUERY_FINISHED]
        tables = {str(table).lower() for event in query_events for table in event.metadata.get("referenced_tables", [])}
        expected_tables = {table.lower() for table in case.required_tables}
        if scenario:
            expected_tables.update(table.lower() for table in scenario.relevant_tables)
        terms = list(case.required_terms)
        if scenario:
            terms.extend([scenario.root_cause, *scenario.expected_effects, *scenario.affected_dimensions.values(), scenario.period.get("start", "")[:7]])
        # A root-cause case needs at least one effect and the root cause; wording is deliberately flexible.
        required_term_hits = [_normalise(str(term)) in answer for term in terms if str(term).strip()]
        root_cause_hit = not scenario or _normalise(scenario.root_cause) in answer
        effects = [_normalise(effect) in answer for effect in (scenario.expected_effects if scenario else [])]
        forbidden = [term for term in case.forbidden_terms if _normalise(term) in answer]
        artifacts = {str(event.metadata.get("artifact_type", "")) for event in events if event.event_type is TraceEventType.ARTIFACT_CREATED}
        security_bypasses = sum(1 for event in events if event.event_type is TraceEventType.TOOL_FINISHED
                                and event.metadata.get("security_bypass") is True)
        query_shapes = [str(event.metadata.get("query_fingerprint", "")) for event in query_events]
        duplicate_queries = sum(count - 1 for count in Counter(shape for shape in query_shapes if shape).values() if count > 1)
        poor_sql = [event for event in query_events if event.metadata.get("select_star") or event.metadata.get("raw_event_query")]
        python_calls = sum(1 for event in events if event.event_type is TraceEventType.ANALYTICS_PYTHON_FINISHED)
        schema_events = {TraceEventType.DATABASE_SCHEMA_LISTED, TraceEventType.DATABASE_TABLE_DESCRIBED,
                         TraceEventType.DATABASE_RELATIONSHIPS_INSPECTED, TraceEventType.DATABASE_SCHEMA_SEARCHED}
        checks = {
            "required_tables": expected_tables.issubset(tables),
            "required_terms": all(required_term_hits) if case.required_terms else True,
            "root_cause": root_cause_hit,
            "effects": all(effects) if effects else True,
            "forbidden_claims_absent": not forbidden,
            "artifacts": set(case.required_artifacts).issubset(artifacts),
            "query_limit": case.max_queries is None or len(query_events) <= case.max_queries,
            "python_use": case.expect_python is None or (python_calls > 0) is case.expect_python,
            "sql_quality": not poor_sql and duplicate_queries == 0,
            "security": security_bypasses == case.expect_security_bypass_count,
        }
        failures = [name.replace("_", " ") for name, passed in checks.items() if not passed]
        metrics = trace.metrics if trace else None
        return AnalyticsCaseResult(case_id=case.id, suite=case.suite, passed=not failures,
            score=sum(checks.values()) / len(checks), checks=checks, failures=failures,
            query_count=len(query_events), schema_inspections=sum(event.event_type in schema_events for event in events),
            duplicate_queries=duplicate_queries,
            failed_queries=sum(event.event_type is TraceEventType.DATABASE_QUERY_FAILED for event in events),
            rejected_queries=sum(event.event_type is TraceEventType.DATABASE_QUERY_REJECTED for event in events),
            python_calls=python_calls, delegations=metrics.delegations if metrics else 0,
            iterations=metrics.iterations if metrics else state.iteration_count,
            tokens=metrics.total_tokens if metrics else None, cost=metrics.estimated_cost if metrics else None,
            latency_ms=metrics.total_duration_ms if metrics else trace.duration_ms if trace else None)


class AnalyticsBenchmarkSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_cases: int
    task_success_rate: float
    root_cause_identification_rate: float
    metric_accuracy: float
    evidence_completeness: float
    unsupported_claim_rate: float
    average_sql_queries: float
    average_iterations: float
    average_tokens: float | None
    average_cost: float | None
    average_latency_ms: float | None
    security_bypass_count: int
    results: list[AnalyticsCaseResult]

    @classmethod
    def from_results(cls, results: list[AnalyticsCaseResult]) -> "AnalyticsBenchmarkSummary":
        def average(values: list[float]) -> float | None: return mean(values) if values else None
        root = [result for result in results if result.suite == "root_cause"]
        metric = [result for result in results if result.suite == "analytics_basic"]
        return cls(total_cases=len(results), task_success_rate=average([float(item.passed) for item in results]) or 0,
            root_cause_identification_rate=average([float(item.checks["root_cause"] and item.checks["effects"]) for item in root]) or 0,
            metric_accuracy=average([float(item.checks["required_terms"]) for item in metric]) or 0,
            evidence_completeness=average([float(item.checks["required_tables"]) for item in results]) or 0,
            unsupported_claim_rate=average([float(not item.checks["forbidden_claims_absent"]) for item in results]) or 0,
            average_sql_queries=average([float(item.query_count) for item in results]) or 0,
            average_iterations=average([float(item.iterations) for item in results]) or 0,
            average_tokens=average([float(item.tokens) for item in results if item.tokens is not None]),
            average_cost=average([item.cost for item in results if item.cost is not None]),
            average_latency_ms=average([float(item.latency_ms) for item in results if item.latency_ms is not None]),
            security_bypass_count=sum(not item.checks["security"] for item in results), results=results)

    def markdown(self, previous: "AnalyticsBenchmarkSummary | None" = None) -> str:
        def delta(name: str, value: float, old: float | None) -> str:
            return f"{value:.1%}" + (f" (previous {old:.1%})" if old is not None else "")
        old = previous
        return "\n".join(["# Data Analyst benchmark", "", f"Cases: {self.total_cases}",
            f"Task success: {delta('success', self.task_success_rate, old.task_success_rate if old else None)}",
            f"Root-cause identification: {delta('root', self.root_cause_identification_rate, old.root_cause_identification_rate if old else None)}",
            f"Metric accuracy: {delta('metric', self.metric_accuracy, old.metric_accuracy if old else None)}",
            f"Evidence completeness: {self.evidence_completeness:.1%}", f"Unsupported-claim rate: {self.unsupported_claim_rate:.1%}",
            f"Average SQL queries: {self.average_sql_queries:.2f}", f"Average iterations: {self.average_iterations:.2f}",
            f"Security bypasses: {self.security_bypass_count}"])
