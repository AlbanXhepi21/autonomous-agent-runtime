"""Recompute a report's factual sections against new parameters.

A reader changes a period, a grouping or a filter and the figures are computed
again — from the metric definitions, not by replaying whatever SQL the agent
happened to write. Replaying that SQL would be the wrong thing twice over: it
was written for one period and hard-codes it, and it was never reviewed as a
reusable statement.

Nothing here calls a model. A rerun is a compilation and an execution, so the
same parameters produce the same figures every time, and a published number
still traces to a query that ran.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.analytics.presentation.charts import ChartSpec, KPIItem
from app.analytics.semantics.compiler import MetricCompilationError
from app.analytics.semantics.execution import MetricExecutionError, MetricResult, MetricRunner
from app.analytics.semantics.parameters import MetricFilter, MetricParameters
from app.contracts.answers import AnswerSource
from app.core.logging import log_event

_logger = logging.getLogger(__name__)

#: Recomputed evidence is numbered in its own series. A rerun must never wear a
#: ``query_###`` identifier: that namespace belongs to the agent's run, and
#: reusing one would make a fresh figure look like the original evidence.
RERUN_PREFIX = "rerun"

#: A report may recompute this many sections at once. A reader is choosing
#: sections, not issuing a workload.
MAX_RERUNS_PER_REPORT = 8


class ReportRerunError(Exception):
    """Raised when a report's parameters cannot be recomputed as asked."""


def rerun_query_id(index: int) -> str:
    """The identifier one recomputed metric is cited under."""

    return f"{RERUN_PREFIX}_{index:03d}"


def describe_filter(item: MetricFilter) -> str:
    """One filter as a reader sees it printed in the appendix."""

    values = item.value if isinstance(item.value, list) else [item.value]
    rendered = ", ".join(str(value) for value in values)
    return f"{item.field} {item.operator} {rendered}"


@dataclass(frozen=True, slots=True)
class RerunOutcome:
    """One recomputed metric: its evidence, its display and its rows."""

    result: MetricResult
    source: AnswerSource
    chart: ChartSpec

    @property
    def query_id(self) -> str:
        return self.source.id


class ReportRerunService:
    """Recompute chosen metrics and hand back citable evidence and displays."""

    def __init__(self, runner: MetricRunner) -> None:
        self._runner = runner

    async def run_all(
        self, *, run_id: str, requests: list[MetricParameters]
    ) -> list[RerunOutcome]:
        """Recompute each request in order, numbering the evidence as it goes."""

        if len(requests) > MAX_RERUNS_PER_REPORT:
            raise ReportRerunError(
                f"A report may recompute at most {MAX_RERUNS_PER_REPORT} metrics at once."
            )
        outcomes: list[RerunOutcome] = []
        for index, parameters in enumerate(requests, start=1):
            outcomes.append(await self._run_one(run_id, index, parameters))
        return outcomes

    async def _run_one(
        self, run_id: str, index: int, parameters: MetricParameters
    ) -> RerunOutcome:
        try:
            result = await self._runner.run(parameters)
        except MetricCompilationError as error:
            # The request named something the metric does not declare, which is
            # a bad request rather than a failure to compute.
            raise ReportRerunError(str(error)) from error
        except MetricExecutionError as error:
            raise ReportRerunError(str(error)) from error

        query_id = rerun_query_id(index)
        source = _source_for(run_id, query_id, result)
        log_event(
            _logger, logging.INFO, "metric_rerun_executed", run_id=run_id,
            query_id=query_id, metric=result.metric,
            period=result.parameters.period.describe(),
            dimensions=list(result.parameters.dimensions),
            row_count=result.row_count, duration_ms=result.execution_ms,
            sql_fingerprint=result.sql_fingerprint,
        )
        return RerunOutcome(result=result, source=source, chart=_display_for(query_id, result))


def _source_for(run_id: str, query_id: str, result: MetricResult) -> AnswerSource:
    """Mint the evidence record for one recomputed metric.

    Built from what the runtime observed — the definition it compiled, the
    parameters it bound, the tables the validator resolved and the shape the
    executor returned. No part of it is authored by a model.
    """

    return AnswerSource(
        id=query_id,
        kind="metric_rerun",
        run_id=run_id,
        label=f"{result.display_name} · {result.parameters.period.describe()}",
        referenced_tables=list(result.tables_consulted)[:16],
        columns=list(result.columns)[:32],
        row_count=result.row_count,
        truncated=result.truncated,
        executed_at=result.executed_at,
        metric=result.metric,
        dimensions=list(result.parameters.dimensions),
        filters=[describe_filter(item) for item in result.parameters.filters][:8],
        sql_fingerprint=result.sql_fingerprint,
    )


def _display_for(query_id: str, result: MetricResult) -> ChartSpec:
    """Turn a recomputed metric into the display a report already knows how to print.

    A grouped result becomes a table of the rows the query returned; an
    ungrouped one becomes KPI cards carrying the exact cell each value was read
    from. Both carry the rows verbatim — nothing is totalled, averaged or
    otherwise derived on the way through.
    """

    rows = [dict(row) for row in result.rows]
    if result.dimension_columns or len(rows) != 1:
        return ChartSpec(
            id=f"{query_id}-table", type="table",
            title=f"{result.display_name} · {result.parameters.period.describe()}",
            description=_describe(result),
            data=rows or [{column: None for column in result.columns}],
            source_query_ids=[query_id],
        )

    row = rows[0]
    return ChartSpec(
        id=f"{query_id}-kpi", type="kpi",
        title=f"{result.display_name} · {result.parameters.period.describe()}",
        description=_describe(result),
        source_query_ids=[query_id],
        kpis=[
            KPIItem(
                label=column.replace("_", " ").capitalize(),
                # Formatted for display; the untouched value travels beside it.
                value=_display_value(row.get(column)),
                raw_value=row.get(column),
                source_column=column,
                source_query_id=query_id,
            )
            for column in result.value_columns if column in row
        ][:8],
    )


def _describe(result: MetricResult) -> str:
    parts = [f"Recomputed from the {result.display_name} definition"]
    if result.parameters.dimensions:
        parts.append("by " + ", ".join(result.parameters.dimensions))
    if result.parameters.filters:
        parts.append("filtered by " + "; ".join(describe_filter(f) for f in result.parameters.filters))
    return ". ".join(parts) + "."


def _display_value(value: object) -> str:
    """Present a value the query returned. Formatting only, never arithmetic."""

    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return f"{value:,}"
    try:
        number = float(str(value))  # Numerics arrive as strings from the driver.
    except (TypeError, ValueError):
        return str(value)
    return f"{number:,.2f}".rstrip("0").rstrip(".")
