"""Storage boundary for execution traces."""

from typing import Protocol

from app.observability.models import RunTrace


class TraceStore(Protocol):
    def save(self, trace: RunTrace) -> None: ...

    def get(self, run_id: str) -> RunTrace | None: ...
