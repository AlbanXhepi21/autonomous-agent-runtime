"""Run tracing."""

from app.composition.lifecycle import provider
from app.observability import InMemoryTraceStore, TraceRecorder


@provider
def get_trace_recorder() -> TraceRecorder:
    """Return the process-local recorder; traces disappear when the API restarts."""

    return TraceRecorder(InMemoryTraceStore())
