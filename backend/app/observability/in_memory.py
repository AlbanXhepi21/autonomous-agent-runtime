"""Process-local trace storage for V7.1."""

from collections import OrderedDict
from threading import RLock

from app.observability.events import RunTrace


class InMemoryTraceStore:
    """Thread-safe, non-persistent trace store; contents vanish on restart."""

    def __init__(self, *, max_traces: int = 1_000) -> None:
        if max_traces < 1:
            raise ValueError("max_traces must be at least 1")
        self._max_traces = max_traces
        self._traces: OrderedDict[str, RunTrace] = OrderedDict()
        self._lock = RLock()

    def save(self, trace: RunTrace) -> None:
        with self._lock:
            self._traces[trace.run_id] = trace.model_copy(deep=True)
            self._traces.move_to_end(trace.run_id)
            while len(self._traces) > self._max_traces:
                self._traces.popitem(last=False)

    def get(self, run_id: str) -> RunTrace | None:
        with self._lock:
            trace = self._traces.get(run_id)
            if trace is not None:
                self._traces.move_to_end(run_id)
            return trace.model_copy(deep=True) if trace else None
