"""Interactive analytical displays are bounded, evidenced, and never executable."""

import pytest

from app.analytics.chart_specs import ChartSpecStore
from app.analytics.datasets import AnalyticsDatasetStore
from app.tools.database.chart import CreateChartTool
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry


def chart_payload() -> dict[str, object]:
    return {
        "type": "line",
        "title": "Monthly revenue for 2026",
        "x_field": "month",
        "y_fields": ["revenue"],
        "series": [{"field": "revenue", "label": "Revenue"}],
        "data": [{"month": "2026-01", "revenue": 100.0}, {"month": "2026-02", "revenue": 120.0}],
        "source_query_ids": ["query_001"],
    }


@pytest.mark.asyncio
async def test_create_chart_persists_a_valid_data_only_spec_for_its_run() -> None:
    datasets = AnalyticsDatasetStore(max_rows=10, max_bytes=10_000)
    assert datasets.register(run_id="r1", query_id="query_001", columns=[{"name": "month"}, {"name": "revenue"}], rows=[["2026-01", 100.0]])
    charts = ChartSpecStore()
    registry = ToolRegistry(); registry.register(CreateChartTool(charts, datasets))

    result = await ToolExecutor(registry).execute("create_chart", {"chart": chart_payload()}, run_id="r1")

    assert result.success
    assert result.output["chart"]["type"] == "line"
    assert charts.list("r1")[0].source_query_ids == ["query_001"]


@pytest.mark.asyncio
async def test_create_chart_rejects_missing_query_evidence_and_executable_fields() -> None:
    datasets = AnalyticsDatasetStore(max_rows=10, max_bytes=10_000)
    registry = ToolRegistry(); registry.register(CreateChartTool(ChartSpecStore(), datasets))
    unsafe = chart_payload(); unsafe["formatter"] = "alert(document.cookie)"

    result = await ToolExecutor(registry).execute("create_chart", {"chart": unsafe}, run_id="r1")

    assert not result.success
    assert result.metadata["failure_category"] == "tool_validation_error"
