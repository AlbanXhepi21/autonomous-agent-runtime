"""Run-scoped, validated analytical display specifications."""

from __future__ import annotations

from app.analytics.presentation.charts import ChartSpec


class ChartSpecStore:
    """Keeps only bounded, data-only specs while a run is active.

    The durable copy is written to the conversation run record at completion.
    This store deliberately contains no executable visualization code.
    """

    def __init__(self) -> None:
        self._specs: dict[str, list[ChartSpec]] = {}

    def add(self, *, run_id: str, chart: ChartSpec) -> ChartSpec:
        charts = self._specs.setdefault(run_id, [])
        if len(charts) >= 8:
            raise ValueError("A run may create at most eight analytical displays.")
        if any(existing.id == chart.id for existing in charts):
            raise ValueError("Chart identifiers must be unique within a run.")
        charts.append(chart)
        return chart

    def list(self, run_id: str) -> list[ChartSpec]:
        return list(self._specs.get(run_id, ()))

