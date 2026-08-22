import pytest

from app.analytics.semantics.metrics import MetricRegistry
from app.tools.database.metric_tools import DescribeMetricTool, ListMetricsTool
from app.tools.execution import ToolExecutor
from app.tools.registry import ToolRegistry


def test_registry_has_required_versioned_metrics_and_edge_case_caveats():
 r=MetricRegistry(); names={x.name for x in r.list_metrics()}
 assert {"revenue","gross_profit","gross_margin_pct","average_order_value","conversion_rate","refund_rate","repeat_purchase_rate","average_delivery_time","campaign_roas"} <= names
 assert r.get_metric_definition("revenue").identifier == "revenue:v1"
 assert "unit_cost" in r.get_metric_definition("gross_profit").formula
 assert "zero" in " ".join(r.get_metric_definition("gross_margin_pct").business_caveats).lower()
 assert "partial" in " ".join(r.get_metric_definition("refund_rate").business_caveats).lower()

@pytest.mark.asyncio
async def test_metric_tools_list_search_and_describe_trusted_configuration():
 r=MetricRegistry(); tools=ToolRegistry(); tools.register(ListMetricsTool(r)); tools.register(DescribeMetricTool(r)); executor=ToolExecutor(tools)
 listed=await executor.execute("list_metrics", {"query":"revenue"}); described=await executor.execute("describe_metric", {"name":"average_order_value"})
 assert listed.success and any(item["name"] == "revenue" for item in listed.output)
 assert described.success and described.output["identifier"] == "average_order_value:v1"
 assert described.output["required_tables"] == ["orders"]
