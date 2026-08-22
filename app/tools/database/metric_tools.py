from typing import Any
from app.analytics.semantics.metrics import MetricRegistry
from app.tools.base import Tool, ToolInputError

class ListMetricsTool(Tool):
 def __init__(self, registry: MetricRegistry): self._registry=registry
 @property
 def name(self): return "list_metrics"
 @property
 def description(self): return "List trusted canonical business metrics available to the analyst."
 @property
 def arguments_schema(self): return {"type":"object","properties":{"query":{"type":"string"}},"required":[],"additionalProperties":False}
 async def execute(self, **arguments: Any):
  items=self._registry.find_metrics(arguments["query"]) if arguments.get("query") else self._registry.list_metrics()
  return [{"name":x.name,"display_name":x.display_name,"version":x.version,"unit":x.unit} for x in items]

class DescribeMetricTool(Tool):
 def __init__(self, registry: MetricRegistry): self._registry=registry
 @property
 def name(self): return "describe_metric"
 @property
 def description(self): return "Return the trusted definition, formula, dimensions, caveats, and version of one business metric."
 @property
 def arguments_schema(self): return {"type":"object","properties":{"name":{"type":"string"}},"required":["name"],"additionalProperties":False}
 async def execute(self, **arguments: Any):
  item=self._registry.get_metric_definition(arguments["name"])
  if not item: raise ToolInputError("Unknown business metric. Use list_metrics to discover available metrics.")
  return item.model_dump() | {"identifier": item.identifier}
