"""Runtime-enforced completion checks for an `InvestigationPlan`.

The model proposes and updates a plan through `update_investigation_plan`, but
nothing here takes its word for a claimed status. `reconcile_plan` downgrades
any question or output the run cannot actually back with evidence it produced,
and `evaluate_finish` decides — from that reconciled plan and the runtime's own
counters, never from anything the model asserts about itself — whether a
`finish` action may be accepted, must be redirected back for more work, or
must be accepted as a bounded partial completion with the gap disclosed.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.contracts.investigation import InvestigationPlan
from app.core.limits import RuntimeLimits
from app.runtime.state import AgentState, Observation


def _successful_outputs(observations: Sequence[Observation], tool_name: str) -> list[dict]:
    """Return the successful ``dict`` outputs of one tool, in run order."""

    outputs: list[dict] = []
    for observation in observations:
        if observation.source != tool_name:
            continue
        content = observation.content
        if not getattr(content, "success", False):
            continue
        output = getattr(content, "output", None)
        if isinstance(output, dict):
            outputs.append(output)
    return outputs


def resolved_query_ids(observations: Sequence[Observation]) -> set[str]:
    """Query references this run actually produced, by their stable id."""

    return {
        output["query_id"]
        for output in _successful_outputs(observations, "query_database")
        if isinstance(output.get("query_id"), str)
    }


def created_display_ids(observations: Sequence[Observation]) -> dict[str, str]:
    """Display ids this run actually created, mapped to their chart type."""

    displays: dict[str, str] = {}
    for output in _successful_outputs(observations, "create_chart"):
        chart_id = output.get("chart_id")
        chart = output.get("chart")
        if isinstance(chart_id, str) and isinstance(chart, dict) and isinstance(chart.get("type"), str):
            displays[chart_id] = chart["type"]
    return displays


def reconcile_plan(plan: InvestigationPlan, observations: Sequence[Observation]) -> InvestigationPlan:
    """Downgrade any claim this run cannot actually support.

    A question claimed "answered" must cite at least one query id this run
    produced; a claim resting on nothing, or on a fabricated reference, reverts
    to "pending". An output claimed "created" must name a display id this run
    actually created through ``create_chart``; otherwise it reverts to
    "pending" too. "blocked" is left alone in both cases — it is a disclosure,
    not a claim of evidence.
    """

    known_queries = resolved_query_ids(observations)
    known_displays = created_display_ids(observations)

    reconciled_questions = []
    for question in plan.questions:
        if question.status == "answered":
            verified = [evidence_id for evidence_id in question.evidence_ids if evidence_id in known_queries]
            if not verified:
                question = question.model_copy(update={"status": "pending", "evidence_ids": []})
            elif verified != question.evidence_ids:
                question = question.model_copy(update={"evidence_ids": verified})
        reconciled_questions.append(question)

    reconciled_outputs = []
    for output in plan.outputs:
        if output.status == "created" and (not output.display_id or output.display_id not in known_displays):
            output = output.model_copy(update={"status": "pending", "display_id": None})
        reconciled_outputs.append(output)

    return plan.model_copy(update={"questions": reconciled_questions, "outputs": reconciled_outputs})


def plan_progress(plan: InvestigationPlan) -> dict[str, int]:
    """A compact, runtime-derived summary a UI or the model can read at a glance."""

    return {
        "questions_answered": sum(1 for q in plan.questions if q.status == "answered"),
        "questions_blocked": sum(1 for q in plan.questions if q.status == "blocked"),
        "questions_total": len(plan.questions),
        "outputs_created": sum(1 for o in plan.outputs if o.status == "created"),
        "outputs_blocked": sum(1 for o in plan.outputs if o.status == "blocked"),
        "outputs_required": len(plan.required_outputs),
        "outputs_total": len(plan.outputs),
        "maximum_displays": plan.maximum_displays,
    }


def _has_created_table(plan: InvestigationPlan, observations: Sequence[Observation]) -> bool:
    if any(output.kind == "table" and output.status == "created" for output in plan.outputs):
        return True
    return "table" in created_display_ids(observations).values()


@dataclass(frozen=True, slots=True)
class FinishEvaluation:
    """What the runtime decided about one `finish` attempt."""

    #: Whether this attempt may become a terminal, completed run.
    accept: bool
    #: Human-readable gaps, disclosed to the model on a redirect and to the
    #: reader as caveats on an accepted partial completion. Empty when nothing
    #: is missing.
    missing: list[str] = field(default_factory=list)


def evaluate_finish(state: AgentState, limits: RuntimeLimits) -> FinishEvaluation:
    """Decide whether `finish` may complete this run.

    Runs with no plan are unaffected — a simple factual question that never
    created one finishes exactly as it always has. A plan's own reconciled
    status, not anything the model states in the `finish` action itself, is
    what this checks.
    """

    plan = state.investigation_plan
    if plan is None:
        return FinishEvaluation(accept=True)

    missing: list[str] = [
        f"Question not yet answered or blocked: {question.question}"
        for question in plan.questions
        if question.status == "pending"
    ]
    missing.extend(
        f"Required output not yet created or blocked: {output.purpose}"
        for output in plan.outputs
        if output.required and output.status == "pending"
    )
    if plan.request_class == "detailed_report" and not _has_created_table(plan, state.observations):
        missing.append("A detailed report was requested but no supporting table has been created.")

    if not missing:
        return FinishEvaluation(accept=True)

    remaining_iterations = limits.max_iterations - state.iteration_count
    remaining_tool_calls = limits.max_tool_calls - state.total_tool_calls
    budget_exhausted = remaining_iterations <= 1 or remaining_tool_calls <= 0
    redirects_exhausted = state.finish_redirect_count >= limits.max_finish_redirects
    if budget_exhausted or redirects_exhausted:
        # Trapping the run indefinitely would be worse than a disclosed gap:
        # accept, but the gap is carried into the answer's caveats by the caller.
        return FinishEvaluation(accept=True, missing=missing)
    return FinishEvaluation(accept=False, missing=missing)
