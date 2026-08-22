"""Parent/child metric aggregation without confusing wall-clock and compute time."""

from pydantic import BaseModel, ConfigDict

from app.observability.models import RunMetrics, RunTrace


class SystemRunMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: RunMetrics
    total_iterations: int = 0
    total_llm_calls: int = 0
    total_tool_calls: int = 0
    total_tokens: int | None = None
    total_estimated_cost: float | None = None
    wall_clock_duration_ms: int | None = None
    child_execution_duration_ms: int = 0


def aggregate_run_metrics(trace: RunTrace, lookup: callable) -> SystemRunMetrics:
    """Sum child compute metrics while retaining root duration as user wall-clock latency."""

    children: list[RunTrace] = []
    ids: set[str] = set()
    for event in trace.events:
        if event.child_run_id:
            ids.add(event.child_run_id)
        if isinstance(event.metadata.get("child_run_ids"), list):
            ids.update(value for value in event.metadata["child_run_ids"] if isinstance(value, str))
    for child_id in ids:
        child = lookup(child_id)
        if child:
            children.append(child)
    child_totals = [aggregate_run_metrics(child, lookup) for child in children]
    all_metrics = [trace.metrics, *(item.root for item in child_totals)]
    token_values = [item.total_tokens for item in all_metrics]
    costs = [item.estimated_cost for item in all_metrics]
    return SystemRunMetrics(
        root=trace.metrics,
        total_iterations=sum(item.iterations for item in all_metrics),
        total_llm_calls=sum(item.llm_calls for item in all_metrics),
        total_tool_calls=sum(item.tool_calls for item in all_metrics),
        total_tokens=sum(value for value in token_values if value is not None) if any(value is not None for value in token_values) else None,
        total_estimated_cost=sum(value for value in costs if value is not None) if costs and all(value is not None for value in costs) else None,
        wall_clock_duration_ms=trace.metrics.total_duration_ms,
        child_execution_duration_ms=sum((child.metrics.total_duration_ms or 0) + item.child_execution_duration_ms
                                        for child, item in zip(children, child_totals, strict=True)),
    )
