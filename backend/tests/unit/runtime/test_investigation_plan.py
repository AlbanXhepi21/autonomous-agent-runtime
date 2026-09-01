"""The typed investigation plan contract and its runtime-enforced completion checks."""

import pytest
from pydantic import ValidationError

from app.contracts.investigation import AnalysisQuestion, InvestigationPlan, PlannedOutput
from app.core.limits import RuntimeLimits
from app.runtime.planning import created_display_ids, evaluate_finish, plan_progress, reconcile_plan, resolved_query_ids
from app.runtime.state import AgentState, Observation
from app.tools.contracts import ToolResult


def question(qid: str = "q1", status: str = "pending", evidence_ids: list[str] | None = None) -> AnalysisQuestion:
    return AnalysisQuestion(id=qid, question="What happened?", status=status, evidence_ids=evidence_ids or [])


def output(oid: str = "o1", *, required: bool = True, status: str = "pending", display_id: str | None = None) -> PlannedOutput:
    return PlannedOutput(id=oid, kind="bar", purpose="Show the breakdown", required=required, status=status, display_id=display_id)


def plan(**overrides: object) -> InvestigationPlan:
    defaults: dict[str, object] = {
        "objective": "Understand the change",
        "request_class": "investigation",
        "questions": [],
        "outputs": [],
        "completion_criteria": [],
        "maximum_displays": 4,
    }
    defaults.update(overrides)
    return InvestigationPlan.model_validate(defaults)


def query_observation(query_id: str, sequence: int = 1) -> Observation:
    return Observation(
        source="query_database", iteration=1, sequence=sequence,
        content=ToolResult(success=True, output={"query_id": query_id, "columns": [], "rows": []}),
    )


def chart_observation(chart_id: str, chart_type: str = "bar", sequence: int = 1) -> Observation:
    return Observation(
        source="create_chart", iteration=1, sequence=sequence,
        content=ToolResult(success=True, output={"chart_id": chart_id, "chart": {"type": chart_type}, "source_query_ids": []}),
    )


# --------------------------------------------------------------------- contract


def test_investigation_plan_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        InvestigationPlan.model_validate({
            "objective": "x", "request_class": "investigation", "maximum_displays": 1,
            "unexpected": True,
        })


def test_investigation_plan_rejects_duplicate_question_ids() -> None:
    with pytest.raises(ValidationError, match="Analysis question ids must be unique"):
        plan(questions=[question("q1").model_dump(), question("q1").model_dump()])


def test_investigation_plan_rejects_duplicate_output_ids() -> None:
    with pytest.raises(ValidationError, match="Planned output ids must be unique"):
        plan(outputs=[output("o1").model_dump(), output("o1").model_dump()])


def test_investigation_plan_bounds_maximum_displays() -> None:
    with pytest.raises(ValidationError):
        plan(maximum_displays=9)
    with pytest.raises(ValidationError):
        plan(maximum_displays=-1)


# --------------------------------------------------------------------- reconciliation


def test_reconcile_keeps_a_question_answered_with_real_evidence() -> None:
    candidate = plan(questions=[question(status="answered", evidence_ids=["query_001"])])

    reconciled = reconcile_plan(candidate, [query_observation("query_001")])

    assert reconciled.questions[0].status == "answered"
    assert reconciled.questions[0].evidence_ids == ["query_001"]


def test_reconcile_resets_a_question_answered_with_fabricated_evidence() -> None:
    candidate = plan(questions=[question(status="answered", evidence_ids=["query_999"])])

    reconciled = reconcile_plan(candidate, [query_observation("query_001")])

    assert reconciled.questions[0].status == "pending"
    assert reconciled.questions[0].evidence_ids == []


def test_reconcile_resets_a_question_answered_with_no_evidence_at_all() -> None:
    candidate = plan(questions=[question(status="answered", evidence_ids=[])])

    reconciled = reconcile_plan(candidate, [])

    assert reconciled.questions[0].status == "pending"


def test_reconcile_drops_only_the_unverifiable_evidence_ids() -> None:
    candidate = plan(questions=[question(status="answered", evidence_ids=["query_001", "query_999"])])

    reconciled = reconcile_plan(candidate, [query_observation("query_001")])

    assert reconciled.questions[0].status == "answered"
    assert reconciled.questions[0].evidence_ids == ["query_001"]


def test_reconcile_keeps_an_output_created_with_a_real_display() -> None:
    candidate = plan(outputs=[output(status="created", display_id="c1")])

    reconciled = reconcile_plan(candidate, [chart_observation("c1")])

    assert reconciled.outputs[0].status == "created"
    assert reconciled.outputs[0].display_id == "c1"


def test_reconcile_resets_an_output_created_with_a_fabricated_display() -> None:
    candidate = plan(outputs=[output(status="created", display_id="does-not-exist")])

    reconciled = reconcile_plan(candidate, [chart_observation("c1")])

    assert reconciled.outputs[0].status == "pending"
    assert reconciled.outputs[0].display_id is None


def test_reconcile_leaves_blocked_items_alone() -> None:
    candidate = plan(
        questions=[question(status="blocked")],
        outputs=[output(status="blocked")],
    )

    reconciled = reconcile_plan(candidate, [])

    assert reconciled.questions[0].status == "blocked"
    assert reconciled.outputs[0].status == "blocked"


def test_resolved_query_ids_and_created_display_ids_ignore_failed_observations() -> None:
    failed_query = Observation(
        source="query_database", iteration=1, sequence=1,
        content=ToolResult(success=False, error="rejected", output=None),
    )

    assert resolved_query_ids([failed_query]) == set()
    assert created_display_ids([failed_query]) == {}
    assert resolved_query_ids([query_observation("query_001")]) == {"query_001"}
    assert created_display_ids([chart_observation("c1", "kpi")]) == {"c1": "kpi"}


# --------------------------------------------------------------------- plan_progress


def test_plan_progress_counts_statuses() -> None:
    candidate = plan(
        questions=[question("q1", status="answered"), question("q2", status="blocked"), question("q3")],
        outputs=[output("o1", status="created"), output("o2", required=False, status="blocked")],
        maximum_displays=5,
    )

    progress = plan_progress(candidate)

    assert progress == {
        "questions_answered": 1, "questions_blocked": 1, "questions_total": 3,
        "outputs_created": 1, "outputs_blocked": 1, "outputs_required": 1, "outputs_total": 2,
        "maximum_displays": 5,
    }


# --------------------------------------------------------------------- evaluate_finish


def _state_with_plan(candidate: InvestigationPlan | None, **overrides: object) -> AgentState:
    state = AgentState(goal="Investigate")
    state.investigation_plan = candidate
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


def test_evaluate_finish_accepts_immediately_when_there_is_no_plan() -> None:
    evaluation = evaluate_finish(_state_with_plan(None), RuntimeLimits())

    assert evaluation.accept
    assert evaluation.missing == []


def test_evaluate_finish_accepts_when_every_required_item_is_resolved() -> None:
    candidate = plan(
        questions=[question(status="answered", evidence_ids=["query_001"])],
        outputs=[output(status="created", display_id="c1")],
    )
    state = _state_with_plan(candidate)
    state.investigation_plan = reconcile_plan(candidate, [query_observation("query_001"), chart_observation("c1")])

    evaluation = evaluate_finish(state, RuntimeLimits())

    assert evaluation.accept
    assert evaluation.missing == []


def test_evaluate_finish_treats_a_non_required_pending_output_as_resolved() -> None:
    candidate = plan(
        questions=[question(status="answered", evidence_ids=["query_001"])],
        outputs=[output(required=False, status="pending")],
    )
    state = _state_with_plan(candidate)
    state.investigation_plan = reconcile_plan(candidate, [query_observation("query_001")])

    evaluation = evaluate_finish(state, RuntimeLimits())

    assert evaluation.accept


def test_evaluate_finish_redirects_when_budget_remains() -> None:
    candidate = plan(questions=[question(status="pending")])
    state = _state_with_plan(candidate, iteration_count=1, total_tool_calls=1)

    evaluation = evaluate_finish(state, RuntimeLimits(max_iterations=8, max_tool_calls=16))

    assert not evaluation.accept
    assert evaluation.missing


def test_evaluate_finish_accepts_a_partial_completion_once_iteration_budget_is_nearly_exhausted() -> None:
    candidate = plan(questions=[question(status="pending")])
    state = _state_with_plan(candidate, iteration_count=7, total_tool_calls=1)

    evaluation = evaluate_finish(state, RuntimeLimits(max_iterations=8, max_tool_calls=16))

    assert evaluation.accept
    assert evaluation.missing


def test_evaluate_finish_accepts_a_partial_completion_once_redirects_are_exhausted() -> None:
    candidate = plan(questions=[question(status="pending")])
    state = _state_with_plan(candidate, iteration_count=1, total_tool_calls=1, finish_redirect_count=2)

    evaluation = evaluate_finish(state, RuntimeLimits(max_iterations=8, max_tool_calls=16, max_finish_redirects=2))

    assert evaluation.accept
    assert evaluation.missing


def test_evaluate_finish_requires_a_supporting_table_for_a_detailed_report() -> None:
    candidate = plan(request_class="detailed_report", outputs=[])
    state = _state_with_plan(candidate, iteration_count=1, total_tool_calls=1)

    evaluation = evaluate_finish(state, RuntimeLimits(max_iterations=8, max_tool_calls=16))

    assert not evaluation.accept
    assert any("supporting table" in item for item in evaluation.missing)


def test_evaluate_finish_accepts_a_detailed_report_once_a_table_was_actually_created() -> None:
    candidate = plan(
        request_class="detailed_report",
        outputs=[PlannedOutput(id="t1", kind="table", purpose="Rows", required=True, status="created", display_id="c1")],
    )
    state = _state_with_plan(candidate, iteration_count=1, total_tool_calls=1)
    state.observations = [chart_observation("c1", "table")]
    state.investigation_plan = reconcile_plan(candidate, state.observations)

    evaluation = evaluate_finish(state, RuntimeLimits(max_iterations=8, max_tool_calls=16))

    assert evaluation.accept
