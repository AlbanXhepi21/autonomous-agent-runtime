"""The agent-facing metric discovery tools surface lifecycle status honestly."""

import pytest

from app.analytics.semantics.metrics import MetricRegistry
from app.tools.base import ToolInputError
from app.tools.database.metric_tools import DescribeMetricTool, ListMetricsTool


@pytest.mark.asyncio
async def test_list_metrics_reports_lifecycle_status_and_rerunnability() -> None:
    tool = ListMetricsTool(MetricRegistry())

    items = await tool.execute(query=None)

    by_name = {item["name"]: item for item in items}
    assert by_name["revenue"]["lifecycle_status"] == "production_ready"
    assert by_name["revenue"]["is_rerunnable"] is True
    assert by_name["cart_to_checkout_rate"]["lifecycle_status"] == "documented"
    assert by_name["cart_to_checkout_rate"]["is_rerunnable"] is False


@pytest.mark.asyncio
async def test_list_metrics_never_reports_a_documented_metric_as_rerunnable() -> None:
    tool = ListMetricsTool(MetricRegistry())

    items = await tool.execute(query=None)

    for item in items:
        if item["lifecycle_status"] == "documented":
            assert item["is_rerunnable"] is False


@pytest.mark.asyncio
async def test_describe_metric_includes_the_lifecycle_status() -> None:
    tool = DescribeMetricTool(MetricRegistry())

    described = await tool.execute(name="cancellation_rate")

    assert described["status"] == "validated"
    assert described["sql_template"] is not None


@pytest.mark.asyncio
async def test_describe_metric_refuses_an_unknown_name() -> None:
    tool = DescribeMetricTool(MetricRegistry())

    with pytest.raises(ToolInputError):
        await tool.execute(name="not_a_real_metric")
