"""Tool for producing safe, interactive ChartSpec payloads for the Workbench."""

from typing import Any

from app.analytics.presentation.chart_store import ChartSpecStore
from app.analytics.presentation.charts import ChartSpec
from app.analytics.semantics.datasets import AnalyticsDatasetStore
from app.tools.base import Tool, ToolInputError


class CreateChartTool(Tool):
    """Accept a bounded declarative chart only after its query evidence exists."""

    operation_kind = "analytics_report"
    requires_run_id = True

    def __init__(self, charts: ChartSpecStore, datasets: AnalyticsDatasetStore) -> None:
        self._charts = charts
        self._datasets = datasets
        self.max_observation_length = 4_000

    @property
    def name(self) -> str:
        return "create_chart"

    @property
    def description(self) -> str:
        return (
            "Create a safe, interactive Workbench chart from a bounded query result. "
            "Use this whenever the result has a shape: three or more rows across a dimension, "
            "a series over time, a composition, a ranking, or a breakdown by two dimensions. "
            "Prefer type 'table' when the reader needs exact figures and 'bar'/'line' when the "
            "comparison or trend is the point. A result with two categorical dimensions and one "
            "measure — a breakdown of one thing by another, such as failures by method and by "
            "reason — is a composition: show it as 'stacked_bar' so the split is visible, and "
            "add a separate 'table' display alongside when the exact figures also matter. "
            "Listing more than three figures in the written "
            "answer instead of creating a display is a mistake. Skip the display only for a "
            "single number, a yes/no answer, or a two-value comparison. "
            "Pass a data-only ChartSpec: supported types are line, bar, stacked_bar, area, pie, "
            "scatter, table, and kpi. Never include JavaScript, HTML, formatter functions, SQL, "
            "or filesystem paths. The source_query_ids must refer to query_database results from "
            "this run, and the data fields must exactly match the supplied rows. Optional formatting is "
            "limited to currency, decimal_places, and show_legend. Prefer this over "
            "a PNG when the user asks for an interactive chart."
        )

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            # Give the model the actual bounded vocabulary rather than an opaque
            # object. Validation remains authoritative at execution time.
            "properties": {"chart": ChartSpec.model_json_schema()},
            "required": ["chart"],
            "additionalProperties": False,
        }

    async def execute_for_run(self, *, run_id: str | None, **arguments: Any) -> dict[str, object]:
        if not run_id:
            raise ToolInputError("Interactive chart creation requires an active run.")
        try:
            chart = ChartSpec.model_validate(arguments["chart"])
        except Exception as error:
            raise ToolInputError(f"Chart specification is invalid: {_validation_summary(error)}") from error
        for query_id in chart.source_query_ids:
            if self._datasets.get(run_id=run_id, dataset_id=f"dataset_{query_id}") is None:
                raise ToolInputError("Chart source_query_ids must reference a bounded query result from this run.")
        try:
            self._charts.add(run_id=run_id, chart=chart)
        except ValueError as error:
            raise ToolInputError(str(error)) from error
        return {"chart": chart.model_dump(mode="json"), "chart_id": chart.id, "source_query_ids": chart.source_query_ids}

    async def execute(self, **arguments: Any) -> dict[str, object]:
        raise ToolInputError("Interactive chart creation requires an active run.")


def _validation_summary(error: Exception) -> str:
    """Return actionable schema guidance without echoing user/model data."""

    errors = getattr(error, "errors", lambda: [])()
    summaries = []
    for item in errors[:4]:
        location = ".".join(str(part) for part in item.get("loc", ()) if str(part) != "chart")
        message = str(item.get("msg", "is invalid")).replace("Value error, ", "")
        summaries.append(f"{location or 'chart'} {message}")
    return "; ".join(summaries) or "use only the documented data-only ChartSpec fields."
