"""Tool for proposing and revising a run's typed investigation plan."""

from typing import Any

from app.contracts.investigation import InvestigationPlan
from app.tools.base import Tool, ToolInputError


class UpdateInvestigationPlanTool(Tool):
    """Accept a bounded, typed investigation plan; validate structure only.

    This tool never decides whether a claimed status is true — a question
    marked "answered" or an output marked "created" is only what the model
    states here. The runtime reconciles those claims against what the run
    actually produced (`app.runtime.planning.reconcile_plan`) immediately
    after this tool returns, before any of it is trusted.
    """

    @property
    def name(self) -> str:
        return "update_investigation_plan"

    @property
    def description(self) -> str:
        return (
            "Create or replace the investigation plan for this run: the objective, its request "
            "class, the analysis questions an answer must resolve, and the displays required to "
            "carry the evidence, within a bounded display budget. Use this before substantial "
            "analysis on a comparison, investigation, executive report, or detailed report; a "
            "simple factual question does not need one. Call it again to update statuses as work "
            "progresses: mark a question 'answered' only once you have cited the query_### "
            "evidence_ids that resolved it, mark an output 'created' with the display_id "
            "create_chart returned, or mark either 'blocked' with the reason understood from the "
            "purpose text. A status the runtime cannot verify against what actually ran is reset "
            "to 'pending' rather than trusted. finish is redirected back to you while a required "
            "question or output remains 'pending' and the runtime has budget left for more work."
        )

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"plan": InvestigationPlan.model_json_schema()},
            "required": ["plan"],
            "additionalProperties": False,
        }

    async def execute(self, **arguments: Any) -> dict[str, object]:
        try:
            plan = InvestigationPlan.model_validate(arguments["plan"])
        except Exception as error:
            raise ToolInputError(f"Investigation plan is invalid: {_validation_summary(error)}") from error
        return {"plan": plan.model_dump(mode="json")}


def _validation_summary(error: Exception) -> str:
    """Return actionable schema guidance without echoing model data verbatim."""

    errors = getattr(error, "errors", lambda: [])()
    summaries = []
    for item in errors[:4]:
        location = ".".join(str(part) for part in item.get("loc", ()) if str(part) != "plan")
        message = str(item.get("msg", "is invalid")).replace("Value error, ", "")
        summaries.append(f"{location or 'plan'} {message}")
    return "; ".join(summaries) or "use only the documented InvestigationPlan fields."
