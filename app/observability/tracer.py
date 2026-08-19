"""Small recorder used by runtime boundaries to build structured run traces."""

from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from app.observability.models import RunMetrics, RunTrace, TraceEvent, TraceEventType, TraceSpan, TraceStatus, sanitize_trace_metadata
from app.observability.store import TraceStore


class TraceRecorder:
    def __init__(self, store: TraceStore) -> None:
        self._store = store
        self._span_started: dict[str, float] = {}

    def get_trace(self, run_id: str) -> RunTrace | None:
        """Return a defensive copy of one sanitized trace."""

        return self._store.get(run_id)

    def start_run(self, *, run_id: str, parent_run_id: str | None, agent_name: str, agent_type: str, goal: str) -> None:
        if self._store.get(run_id):
            return
        trace = RunTrace(run_id=run_id, parent_run_id=parent_run_id, agent_name=agent_name,
                         agent_type=agent_type, goal=sanitize_trace_metadata({"goal": goal})["goal"])
        trace.events.append(TraceEvent(run_id=run_id, parent_run_id=parent_run_id,
            event_type=TraceEventType.RUN_STARTED, status=TraceStatus.RUNNING))
        self._store.save(trace)

    def record(self, run_id: str, event_type: TraceEventType, *, parent_run_id: str | None = None,
               child_run_id: str | None = None, iteration: int | None = None,
               duration_ms: int | None = None, status: TraceStatus | None = None,
               success: bool | None = None, metadata: dict[str, Any] | None = None,
               span_id: str | None = None, parent_span_id: str | None = None) -> None:
        trace = self._store.get(run_id)
        if trace is None:
            return
        trace.events.append(TraceEvent(run_id=run_id, parent_run_id=parent_run_id or trace.parent_run_id,
            child_run_id=child_run_id, event_type=event_type, iteration=iteration, duration_ms=duration_ms,
            status=status, success=success, metadata=sanitize_trace_metadata(metadata), span_id=span_id,
            parent_span_id=parent_span_id))
        self._store.save(trace)

    def start_span(self, run_id: str, event_type: TraceEventType, *, name: str, iteration: int | None = None,
                   parent_span_id: str | None = None, metadata: dict[str, Any] | None = None) -> str:
        trace = self._store.get(run_id)
        if trace is None:
            return ""
        span = TraceSpan(run_id=run_id, parent_span_id=parent_span_id, name=name, event_type=event_type,
                         metadata=sanitize_trace_metadata(metadata))
        trace.spans.append(span)
        self._span_started[span.span_id] = perf_counter()
        self._store.save(trace)
        self.record(run_id, event_type, iteration=iteration, metadata=metadata, span_id=span.span_id,
                    parent_span_id=parent_span_id)
        return span.span_id

    def finish_span(self, run_id: str, span_id: str, event_type: TraceEventType, *, iteration: int | None = None,
                    success: bool, metadata: dict[str, Any] | None = None) -> None:
        trace = self._store.get(run_id)
        if trace is None:
            return
        duration_ms = round((perf_counter() - self._span_started.pop(span_id, perf_counter())) * 1000)
        for span in trace.spans:
            if span.span_id == span_id:
                span.ended_at = datetime.now(timezone.utc)
                span.duration_ms = duration_ms
                span.status = TraceStatus.COMPLETED if success else TraceStatus.FAILED
                break
        self._store.save(trace)
        self.record(run_id, event_type, iteration=iteration, duration_ms=duration_ms, success=success,
                    metadata=metadata, span_id=span_id)

    def finish_run(self, run_id: str, *, status: TraceStatus, stop_reason: str | None,
                   metrics: dict[str, int]) -> None:
        trace = self._store.get(run_id)
        if trace is None:
            return
        trace.ended_at = datetime.now(timezone.utc)
        trace.duration_ms = round((trace.ended_at - trace.started_at).total_seconds() * 1000)
        trace.status, trace.stop_reason = status, stop_reason
        event_type = TraceEventType.RUN_FINISHED if status is TraceStatus.COMPLETED else TraceEventType.RUN_FAILED
        trace.events.append(TraceEvent(run_id=run_id, parent_run_id=trace.parent_run_id, event_type=event_type,
            duration_ms=trace.duration_ms, status=status, success=status is TraceStatus.COMPLETED,
            metadata={"stop_reason": stop_reason, **metrics}))
        trace.metrics = _derive_metrics(trace, metrics)
        self._store.save(trace)


def _derive_metrics(trace: RunTrace, base: dict[str, int]) -> RunMetrics:
    """Aggregate only the sanitized numeric usage and timing already in this trace."""

    llm_events = [event for event in trace.events if event.event_type is TraceEventType.LLM_REQUEST_FINISHED]
    llm_attempts = [event for event in trace.events if event.event_type in {TraceEventType.LLM_REQUEST_FINISHED, TraceEventType.LLM_REQUEST_FAILED}]
    def values(key: str) -> list[int]:
        return [value for event in llm_events if isinstance((value := event.metadata.get(key)), int)]
    costs = [value for event in llm_events if isinstance((value := event.metadata.get("estimated_cost")), (int, float))]
    durations = lambda event_type: sum(event.duration_ms or 0 for event in trace.events if event.event_type is event_type)
    input_tokens, output_tokens = values("input_tokens"), values("output_tokens")
    cached_tokens, reasoning_tokens = values("cached_input_tokens"), values("reasoning_tokens")
    return RunMetrics(
        iterations=base.get("iterations", 0), tool_calls=base.get("tool_calls", 0),
        delegations=base.get("delegations", 0), llm_calls=len(llm_attempts),
        input_tokens=sum(input_tokens) if input_tokens else None, output_tokens=sum(output_tokens) if output_tokens else None,
        cached_input_tokens=sum(cached_tokens) if cached_tokens else None, reasoning_tokens=sum(reasoning_tokens) if reasoning_tokens else None,
        total_tokens=(sum(input_tokens) + sum(output_tokens)) if input_tokens or output_tokens else None,
        estimated_cost=sum(costs) if costs and len(costs) == len(llm_events) else None,
        llm_duration_ms=sum(event.duration_ms or 0 for event in llm_attempts),
        tool_duration_ms=sum(event.duration_ms or 0 for event in trace.events if event.event_type in {TraceEventType.TOOL_FINISHED, TraceEventType.TOOL_FAILED}),
        memory_duration_ms=durations(TraceEventType.MEMORY_RETRIEVAL_FINISHED),
        summary_duration_ms=durations(TraceEventType.TASK_SUMMARY_FINISHED),
        delegation_duration_ms=sum(event.duration_ms or 0 for event in trace.events if event.event_type in {TraceEventType.DELEGATION_FINISHED, TraceEventType.PARALLEL_DELEGATION_FINISHED}),
        total_duration_ms=trace.duration_ms,
    )
