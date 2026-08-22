"""DA7 evaluation-only benchmark coverage."""

from pathlib import Path

import pytest

from app.observability import RunMetrics, RunTrace, TraceEvent, TraceEventType
from app.runtime.state import AgentState, RunStatus
from app.tools.execution.redaction import query_quality_metadata
from evals.analytics import (
    AnalyticsBenchmarkSummary,
    DeterministicAnalyticsEvaluator,
    GroundTruthLoader,
    load_analytics_dataset,
)
from tests.support import REPO_ROOT

ROOT = REPO_ROOT
DATASET = ROOT / "evals" / "datasets" / "analytics_cases.json"
# Ground truth lives in the sibling data-generator repository, which is not part
# of this one. Cases that compare against it are skipped when it is not checked
# out beside this repository rather than failing a clone that has only this.
GROUND_TRUTH = ROOT.parents[0] / "DataGenerator" / "generator" / "ground_truth" / "scenarios.json"
needs_ground_truth = pytest.mark.skipif(
    not GROUND_TRUTH.exists(), reason=f"ground truth not present at {GROUND_TRUTH}"
)


def state(answer: str) -> AgentState:
    return AgentState(goal="Evaluate", completed=True, status=RunStatus.COMPLETED, final_answer=answer)


def trace(*tables: str, artifact_type: str | None = None) -> RunTrace:
    events = [TraceEvent(run_id="run", event_type=TraceEventType.DATABASE_QUERY_FINISHED,
                         metadata={"referenced_tables": list(tables), "query_fingerprint": "one"})]
    if artifact_type:
        events.append(TraceEvent(run_id="run", event_type=TraceEventType.ARTIFACT_CREATED,
                                 metadata={"artifact_type": artifact_type}))
    return RunTrace(run_id="run", agent_name="data_analyst", agent_type="specialist", goal="Evaluate",
                    events=events, metrics=RunMetrics(iterations=3, database_query_count=1, total_duration_ms=9))


@needs_ground_truth
def test_ground_truth_is_loaded_only_by_evaluator_and_cases_are_opaque() -> None:
    scenarios = GroundTruthLoader.load(GROUND_TRUTH)
    dataset = load_analytics_dataset(DATASET)
    assert len(dataset.cases) == 26
    assert {case.suite for case in dataset.cases} == {"analytics_basic", "sales", "profitability", "marketing", "customers", "operations", "inventory", "root_cause", "security", "reporting", "advanced"}
    mobile = next(case for case in dataset.cases if case.id == "root_cause.mobile_checkout")
    assert mobile.ground_truth_id == "mobile_checkout_failure_2026_04"
    assert scenarios[mobile.ground_truth_id].root_cause not in mobile.question
    runtime_sources = list((ROOT / "app").rglob("*.py"))
    assert all("DataGenerator" not in source.read_text(encoding="utf-8") for source in runtime_sources if "evals" not in source.parts)


@needs_ground_truth
def test_root_cause_uses_evidence_not_exact_case_wording() -> None:
    scenarios = GroundTruthLoader.load(GROUND_TRUTH)
    case = next(item for item in load_analytics_dataset(DATASET).cases if item.id == "root_cause.mobile_checkout")
    result = DeterministicAnalyticsEvaluator(scenarios).evaluate(
        case, state("April 2026 revenue declined. Mobile checkout regression: checkout errors increase and mobile conversion decreases."),
        trace("orders", "web_sessions", "web_events"))
    assert result.passed and result.checks["required_tables"] and result.checks["root_cause"]


def test_sql_quality_security_and_summary_checks() -> None:
    quality = query_quality_metadata("SELECT * FROM web_events")
    assert quality["select_star"] and quality["raw_event_query"] and "sql" not in quality
    case = next(item for item in load_analytics_dataset(DATASET).cases if item.id == "reporting.executive")
    result = DeterministicAnalyticsEvaluator().evaluate(case, state("Executive summary: marketing results."), trace("orders", artifact_type="report"))
    assert result.passed
    summary = AnalyticsBenchmarkSummary.from_results([result])
    assert summary.task_success_rate == 1 and "# Data Analyst benchmark" in summary.markdown()


def test_advanced_cases_and_guidance_remain_generic() -> None:
    cases = load_analytics_dataset(DATASET).cases
    advanced = [case for case in cases if case.suite == "advanced"]
    assert len(advanced) == 6
    guidance = (ROOT / "app" / "resources" / "skills" / "data_analysis" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert all(term in guidance for term in ("contribution analysis", "funnel", "cohort", "iqr", "causal"))
    assert "delegate" not in guidance
