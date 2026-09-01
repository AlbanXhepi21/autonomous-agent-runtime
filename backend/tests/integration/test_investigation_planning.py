"""End-to-end investigation-planning scenarios, scripted through the real runner loop.

`query_database` and its dataset registration are faked (as in
`tests/integration/test_data_analyst.py`) so these tests exercise runtime
planning behavior rather than the Postgres-backed SQL boundary, which is
already covered elsewhere. `create_chart` and `ChartSpecStore` are the real
implementations, so display persistence is genuinely exercised.
"""

from typing import Any

import pytest

from app.analytics.presentation.chart_store import ChartSpecStore
from app.analytics.semantics.datasets import AnalyticsDatasetStore
from app.contracts.actions import AgentAction
from app.core.limits import RuntimeLimits
from app.runtime.state import StopReason
from app.tools.base import Tool, ToolInputError
from app.tools.database.chart import CreateChartTool
from app.tools.planning import UpdateInvestigationPlanTool
from app.tools.registry import ToolRegistry
from tests.support import ScriptedLLM, make_runner


class FakeQueryTool(Tool):
    """Stands in for `query_database`: same tool name, dataset registration, and
    query numbering (via the shared executor observers), no real database."""

    requires_run_id = True

    def __init__(self, datasets: AnalyticsDatasetStore) -> None:
        self._datasets = datasets

    @property
    def name(self) -> str:
        return "query_database"

    @property
    def description(self) -> str:
        return "Fake bounded read-only query."

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"sql": {"type": "string"}, "purpose": {"type": "string"}},
            "required": ["sql"],
            "additionalProperties": False,
        }

    async def execute_for_run(self, *, run_id: str | None, query_id: str, **arguments: Any) -> dict[str, Any]:
        columns = [{"name": "month"}, {"name": "value"}]
        rows = [["2026-01", 100], ["2026-02", 120]]
        if run_id:
            self._datasets.register(run_id=run_id, query_id=query_id, columns=columns, rows=rows)
        return {"columns": columns, "rows": rows, "row_count": len(rows), "truncated": False, "referenced_tables": ["orders"]}

    async def execute(self, **arguments: Any) -> dict[str, Any]:
        raise ToolInputError("query_database requires an active run.")


def build_tools() -> tuple[ToolRegistry, ChartSpecStore]:
    datasets = AnalyticsDatasetStore(max_rows=1_000, max_bytes=1_000_000)
    charts = ChartSpecStore()
    registry = ToolRegistry()
    registry.register(UpdateInvestigationPlanTool())
    registry.register(FakeQueryTool(datasets))
    registry.register(CreateChartTool(charts, datasets))
    return registry, charts


def question(qid: str, text: str, *, status: str = "pending", evidence_ids: list[str] | None = None) -> dict[str, Any]:
    return {"id": qid, "question": text, "status": status, "evidence_ids": evidence_ids or []}


def output(
    oid: str, kind: str, purpose: str, *, required: bool = True, status: str = "pending", display_id: str | None = None
) -> dict[str, Any]:
    return {"id": oid, "kind": kind, "purpose": purpose, "required": required, "status": status, "display_id": display_id}


def plan(
    *, objective: str, request_class: str, questions: list[dict[str, Any]], outputs: list[dict[str, Any]],
    maximum_displays: int, completion_criteria: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "objective": objective, "request_class": request_class, "questions": questions, "outputs": outputs,
        "completion_criteria": completion_criteria or [], "maximum_displays": maximum_displays,
    }


def plan_action(payload: dict[str, Any]) -> AgentAction:
    return AgentAction(
        action_type="use_tool", reasoning_summary="Plan the investigation.",
        tool_name="update_investigation_plan", tool_arguments={"plan": payload},
    )


def query_action(sql: str = "SELECT value FROM orders") -> AgentAction:
    return AgentAction(
        action_type="use_tool", reasoning_summary="Gather evidence.",
        tool_name="query_database", tool_arguments={"sql": sql, "purpose": sql},
    )


def chart_payload(chart_id: str, chart_type: str, query_id: str) -> dict[str, Any]:
    if chart_type == "kpi":
        return {
            "id": chart_id, "type": "kpi", "title": "Headline figure",
            "kpis": [{"label": "Total", "value": "120", "source_query_id": query_id}],
            "source_query_ids": [query_id],
        }
    if chart_type == "table":
        return {
            "id": chart_id, "type": "table", "title": "Supporting rows",
            "data": [{"month": "2026-01", "value": 100}, {"month": "2026-02", "value": 120}],
            "source_query_ids": [query_id],
        }
    return {
        "id": chart_id, "type": chart_type, "title": "Trend",
        "x_field": "month", "y_fields": ["value"],
        "data": [{"month": "2026-01", "value": 100}, {"month": "2026-02", "value": 120}],
        "source_query_ids": [query_id],
    }


def chart_action(chart_id: str, chart_type: str, query_id: str) -> AgentAction:
    return AgentAction(
        action_type="use_tool", reasoning_summary="Create a display.",
        tool_name="create_chart", tool_arguments={"chart": chart_payload(chart_id, chart_type, query_id)},
    )


def finish_action(answer: str, *, citations: list[str] | None = None, caveats: list[str] | None = None) -> AgentAction:
    return AgentAction(
        action_type="finish", reasoning_summary="The evidence answers the question.",
        final_answer=answer, citations=citations or [], caveats=caveats or [],
    )


# ------------------------------------------------------------------- scenarios


@pytest.mark.asyncio
async def test_simple_factual_question_finishes_without_a_plan_or_a_forced_display() -> None:
    registry, charts = build_tools()
    runner = make_runner(ScriptedLLM([finish_action("Total revenue was $1,000.")]), registry)

    state = await runner.run("What is total revenue?")

    assert state.completed
    assert state.investigation_plan is None
    assert charts.list(state.run_id) == []


@pytest.mark.asyncio
async def test_comparison_request_plans_and_creates_one_comparison_display() -> None:
    registry, charts = build_tools()
    initial = plan(
        objective="Compare this month's revenue to last month's", request_class="comparison",
        questions=[question("q1", "How does this month compare to last month?")],
        outputs=[output("o1", "bar", "Month-over-month revenue comparison")],
        maximum_displays=2,
    )
    updated = plan(
        objective=initial["objective"], request_class="comparison",
        questions=[question("q1", "How does this month compare to last month?", status="answered", evidence_ids=["query_001"])],
        outputs=[output("o1", "bar", "Month-over-month revenue comparison", status="created", display_id="c1")],
        maximum_displays=2,
    )
    llm = ScriptedLLM([
        plan_action(initial),
        query_action(),
        chart_action("c1", "bar", "query_001"),
        plan_action(updated),
        finish_action("Revenue rose from $100 to $120 month over month.", citations=["query_001"]),
    ])
    runner = make_runner(llm, registry, limits=RuntimeLimits(max_iterations=10, max_tool_calls=10))

    state = await runner.run("How does revenue compare to last month?")

    assert state.completed
    assert state.investigation_plan is not None
    assert state.investigation_plan.questions[0].status == "answered"
    assert state.investigation_plan.outputs[0].status == "created"
    persisted = charts.list(state.run_id)
    assert len(persisted) == 1
    assert persisted[0].type == "bar"


@pytest.mark.asyncio
async def test_executive_investigation_plans_and_creates_several_useful_outputs() -> None:
    registry, charts = build_tools()
    initial = plan(
        objective="Analyze payment failures in 2026", request_class="executive_report",
        questions=[
            question("q1", "What is the total failure volume?"),
            question("q2", "What is the breakdown by method and reason?"),
            question("q3", "How does the failure rate trend by month?"),
        ],
        outputs=[
            output("o1", "kpi", "Total failure volume"),
            output("o2", "stacked_bar", "Failures by method and reason"),
            output("o3", "line", "Monthly failure trend"),
            output("o4", "table", "Supporting detail rows", required=False),
        ],
        maximum_displays=6,
    )
    final = plan(
        objective=initial["objective"], request_class="executive_report",
        questions=[
            question("q1", "What is the total failure volume?", status="answered", evidence_ids=["query_001"]),
            question("q2", "What is the breakdown by method and reason?", status="answered", evidence_ids=["query_002"]),
            question("q3", "How does the failure rate trend by month?", status="answered", evidence_ids=["query_003"]),
        ],
        outputs=[
            output("o1", "kpi", "Total failure volume", status="created", display_id="c1"),
            output("o2", "stacked_bar", "Failures by method and reason", status="created", display_id="c2"),
            output("o3", "line", "Monthly failure trend", status="created", display_id="c3"),
            output("o4", "table", "Supporting detail rows", required=False, status="skipped"),
        ],
        maximum_displays=6,
    )
    llm = ScriptedLLM([
        plan_action(initial),
        query_action("SELECT COUNT(*) FROM payments WHERE status = 'failed'"),
        chart_action("c1", "kpi", "query_001"),
        query_action("SELECT method, reason, COUNT(*) FROM payments GROUP BY method, reason"),
        chart_action("c2", "stacked_bar", "query_002"),
        query_action("SELECT month, COUNT(*) FROM payments GROUP BY month"),
        chart_action("c3", "line", "query_003"),
        plan_action(final),
        finish_action(
            "Payment failures totaled 120 in 2026, concentrated in card declines.",
            citations=["query_001", "query_002", "query_003"],
        ),
    ])
    runner = make_runner(llm, registry, limits=RuntimeLimits(max_iterations=12, max_tool_calls=12))

    state = await runner.run("Create an executive analysis of payment failures in 2026.")

    assert state.completed
    assert state.finish_redirect_count == 0
    persisted = charts.list(state.run_id)
    assert len(persisted) == 3
    assert {chart.type for chart in persisted} == {"kpi", "stacked_bar", "line"}
    assert state.investigation_plan is not None
    required_statuses = {o.status for o in state.investigation_plan.outputs if o.required}
    assert required_statuses == {"created"}


@pytest.mark.asyncio
async def test_multiple_displays_are_persisted_within_one_run() -> None:
    registry, charts = build_tools()
    llm = ScriptedLLM([
        query_action(),
        chart_action("c1", "line", "query_001"),
        query_action(),
        chart_action("c2", "bar", "query_002"),
        finish_action("The trend rose; the channel comparison is above.", citations=["query_001", "query_002"]),
    ])
    runner = make_runner(llm, registry, limits=RuntimeLimits(max_iterations=8, max_tool_calls=8))

    state = await runner.run("Show revenue trend and a channel comparison.")

    assert state.completed
    persisted = charts.list(state.run_id)
    assert len(persisted) == 2
    assert {chart.id for chart in persisted} == {"c1", "c2"}


@pytest.mark.asyncio
async def test_finish_is_redirected_while_a_required_output_remains_achievable() -> None:
    registry, charts = build_tools()
    initial = plan(
        objective="Investigate the drop in conversion", request_class="investigation",
        questions=[question("q1", "What caused the conversion drop?")],
        outputs=[output("o1", "bar", "Conversion by channel")],
        maximum_displays=4,
    )
    updated = plan(
        objective=initial["objective"], request_class="investigation",
        questions=[question("q1", "What caused the conversion drop?", status="answered", evidence_ids=["query_001"])],
        outputs=[output("o1", "bar", "Conversion by channel", status="created", display_id="c1")],
        maximum_displays=4,
    )
    llm = ScriptedLLM([
        plan_action(initial),
        finish_action("Conversion dropped because of mobile checkout errors."),
        query_action(),
        chart_action("c1", "bar", "query_001"),
        plan_action(updated),
        finish_action(
            "Conversion dropped because of mobile checkout errors, visible in the channel breakdown.",
            citations=["query_001"],
        ),
    ])
    runner = make_runner(llm, registry, limits=RuntimeLimits(max_iterations=10, max_tool_calls=10))

    state = await runner.run("Why did conversion drop?")

    assert state.completed
    assert state.finish_redirect_count == 1
    redirected = [observation for observation in state.observations if observation.source == "investigation_plan"]
    assert len(redirected) == 1
    assert not redirected[0].content.success
    assert "Required output not yet created" in (redirected[0].content.error or "")
    assert len(charts.list(state.run_id)) == 1


@pytest.mark.asyncio
async def test_partial_finish_once_finish_redirects_are_exhausted() -> None:
    registry, _ = build_tools()
    initial = plan(
        objective="Investigate refunds", request_class="investigation",
        questions=[question("q1", "Why did refunds increase?")],
        outputs=[output("o1", "bar", "Refunds by category")],
        maximum_displays=4,
    )
    llm = ScriptedLLM([
        plan_action(initial),
        finish_action("Refunds increased due to a shipping issue."),
        finish_action("Refunds increased due to a shipping issue."),
    ])
    runner = make_runner(
        llm, registry, limits=RuntimeLimits(max_iterations=6, max_tool_calls=6, max_finish_redirects=1),
    )

    state = await runner.run("Why did refunds increase?")

    assert state.completed
    assert state.stop_reason is StopReason.COMPLETED
    assert state.finish_redirect_count == 1
    assert any(caveat.startswith("Incomplete:") for caveat in state.answer_caveats)


@pytest.mark.asyncio
async def test_partial_finish_once_iteration_budget_is_nearly_exhausted() -> None:
    registry, _ = build_tools()
    initial = plan(
        objective="Investigate refunds", request_class="investigation",
        questions=[question("q1", "Why did refunds increase?")],
        outputs=[output("o1", "bar", "Refunds by category")],
        maximum_displays=4,
    )
    llm = ScriptedLLM([plan_action(initial), finish_action("Refunds increased due to a shipping issue.")])
    runner = make_runner(llm, registry, limits=RuntimeLimits(max_iterations=2, max_tool_calls=6))

    state = await runner.run("Why did refunds increase?")

    assert state.completed
    assert state.finish_redirect_count == 0
    assert any(caveat.startswith("Incomplete:") for caveat in state.answer_caveats)


@pytest.mark.asyncio
async def test_a_question_marked_answered_without_verifiable_evidence_is_reset_to_pending() -> None:
    registry, _ = build_tools()
    fabricated = plan(
        objective="Understand the spike in refunds", request_class="investigation",
        questions=[question("q1", "Why did refunds spike?", status="answered", evidence_ids=["query_999"])],
        outputs=[],
        maximum_displays=4,
    )
    llm = ScriptedLLM([plan_action(fabricated)])
    runner = make_runner(llm, registry, limits=RuntimeLimits(max_iterations=1))

    state = await runner.run("Why did refunds spike?")

    assert state.investigation_plan is not None
    assert state.investigation_plan.questions[0].status == "pending"
    assert state.investigation_plan.questions[0].evidence_ids == []


@pytest.mark.asyncio
async def test_investigation_plan_survives_observation_compaction() -> None:
    registry, _ = build_tools()
    initial = plan(
        objective="Investigate the revenue trend", request_class="investigation",
        questions=[question("q1", "What drove the revenue trend?")],
        outputs=[output("o1", "line", "Monthly revenue trend")],
        maximum_displays=4,
    )
    actions = [plan_action(initial)] + [query_action(f"SELECT {i}") for i in range(9)] + [
        finish_action("Revenue trended upward.", citations=["query_001"])
    ]
    llm = ScriptedLLM(actions)
    runner = make_runner(llm, registry, limits=RuntimeLimits(max_iterations=20, max_tool_calls=20))

    state = await runner.run("What drove the revenue trend?")

    assert state.completed
    assert state.task_summary is not None
    assert state.task_summary.summarized_observation_count > 0
    assert state.investigation_plan is not None
    assert state.investigation_plan.questions[0].id == "q1"
    contexts_after_plan_created = llm.contexts[1:]
    assert contexts_after_plan_created
    assert all(context["investigation_plan"] is not None for context in contexts_after_plan_created)


@pytest.mark.asyncio
async def test_plan_with_no_required_outputs_does_not_force_any_display() -> None:
    registry, charts = build_tools()
    initial = plan(
        objective="Confirm whether refunds increased", request_class="investigation",
        questions=[question("q1", "Did refunds increase?")],
        outputs=[],
        maximum_displays=4,
        completion_criteria=["State whether refunds increased, with evidence."],
    )
    updated = plan(
        objective=initial["objective"], request_class="investigation",
        questions=[question("q1", "Did refunds increase?", status="answered", evidence_ids=["query_001"])],
        outputs=[],
        maximum_displays=4,
        completion_criteria=initial["completion_criteria"],
    )
    llm = ScriptedLLM([
        plan_action(initial),
        query_action(),
        plan_action(updated),
        finish_action("Refunds did not increase.", citations=["query_001"]),
    ])
    runner = make_runner(llm, registry, limits=RuntimeLimits(max_iterations=8, max_tool_calls=8))

    state = await runner.run("Did refunds increase?")

    assert state.completed
    assert state.finish_redirect_count == 0
    assert charts.list(state.run_id) == []
