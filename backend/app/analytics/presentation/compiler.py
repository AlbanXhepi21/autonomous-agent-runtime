"""Compile one finished run into the canonical report both renderers read.

This is the only place that decides what a report contains. It reads what the
run already produced — the written answer, the validated displays, the resolved
evidence registry, the stated limitations — and lays them out in the order a
template asks for. Every fact is carried across verbatim, together with the
query it came from.

What this module may do to a fact: select it, order it, label it, and pass
through a display string the run already produced. What it may not do, ever:
add, average, count, compute a percentage, take a difference, or supply a value
the run did not produce. A figure that is not in the run does not appear in the
report.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from uuid import uuid4

from app.analytics.presentation.charts import ChartSpec, KPIItem
from app.analytics.presentation.document_model import (
    CaveatsBlock,
    ChartBlock,
    CompiledMetric,
    CompiledReport,
    CompiledRows,
    CoverBlock,
    EvidenceBlock,
    EvidenceEntry,
    MetricsBlock,
    NarrativeBlock,
    PageBreakBlock,
    ProseLine,
    ReportBlock,
    RowSelector,
    NarrativeStatus,
    ScopeBlock,
    ScopeRow,
    TableBlock,
)
from app.analytics.presentation.rasterize import RASTERIZABLE
from app.analytics.presentation.templates import ReportTemplate
from app.contracts.answers import AnswerSource

#: What a citation does and does not establish. A resolved citation proves the
#: query ran and returned what the ledger recorded; it says nothing about whether
#: a sentence in the narrative follows arithmetically from those rows. Printing
#: that distinction is the honest thing to do, so it is stated on every report
#: that cites anything rather than left for a reader to assume either way.
CITATION_NOTICE = (
    "Query citations confirm that the referenced query executed. They do not "
    "independently verify that every narrative conclusion was mathematically "
    "derived from that query."
)

#: Said on a DOCX, which a reader can edit after it leaves here. The PDF is the
#: deliverable whose figures are the ones this run produced.
EDITABLE_COPY_NOTICE = (
    "This Word copy is provided for editing and reuse. Once edited it is no "
    "longer a record of what the run produced; the PDF is the published report."
)

_HEADING = re.compile(r"^(#{1,4})\s+(.*)$")
_BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
_NUMBERED = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_EMPHASIS = re.compile(r"\*\*(.+?)\*\*|__(.+?)__|\*(.+?)\*|`(.+?)`")

#: Rows of a table carried into a document before it stops being readable.
MAX_DOCUMENT_TABLE_ROWS = 50


def narrative_warning(status: NarrativeStatus, written_for: str | None, showing: str | None) -> str | None:
    """The sentence a reader needs when the prose and the figures disagree.

    Returned rather than printed, so both renderers show the same words and
    neither can decide to leave it out.
    """

    if status != "pinned_to_original_period":
        return None
    original = written_for or "the original period"
    refreshed = showing or "a different period"
    return (
        f"This narrative was written for {original} and has been kept unchanged. "
        f"The figures in this report were recomputed for {refreshed}. "
        "The wording below does not describe them."
    )


def strip_emphasis(text: str) -> str:
    """Remove inline Markdown markers, keeping the words they wrapped."""

    return _EMPHASIS.sub(lambda match: next(group for group in match.groups() if group is not None), text)


def parse_prose(markdown: str) -> list[ProseLine]:
    """Read the written answer as document lines.

    A deliberately small subset — headings, lists and paragraphs — because the
    answer is prose an analyst wrote for a reader, not a document format. What
    is not recognised stays a paragraph rather than being dropped.
    """

    lines: list[ProseLine] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            text = strip_emphasis(" ".join(paragraph).strip())
            if text:
                lines.append(ProseLine(kind="paragraph", text=text))
            paragraph.clear()

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue
        if heading := _HEADING.match(line):
            flush()
            text = strip_emphasis(heading.group(2).strip())
            if text:
                lines.append(ProseLine(kind="heading", text=text, level=len(heading.group(1))))
        elif bullet := _BULLET.match(line):
            flush()
            if text := strip_emphasis(bullet.group(1).strip()):
                lines.append(ProseLine(kind="bullet", text=text))
        elif numbered := _NUMBERED.match(line):
            flush()
            if text := strip_emphasis(numbered.group(1).strip()):
                lines.append(ProseLine(kind="number", text=text))
        else:
            paragraph.append(line.strip())
    flush()
    return lines


def describe_source(source: AnswerSource) -> str:
    """One line of provenance a reader can check, never the SQL."""

    parts = [source.label]
    if source.referenced_tables:
        parts.append(", ".join(source.referenced_tables))
    if source.row_count is not None:
        parts.append(f"{source.row_count:,} row{'' if source.row_count == 1 else 's'}")
    if source.truncated:
        parts.append("result truncated")
    return " · ".join(parts)


def _rows_of(chart: ChartSpec, *, limit: int | None = None) -> CompiledRows:
    """Carry a display's own rows across, exactly as it holds them."""

    rows = chart.data if limit is None else chart.data[:limit]
    columns = list(chart.data[0].keys()) if chart.data else []
    return CompiledRows(
        columns=columns[:32],
        rows=[{key: row.get(key) for key in columns} for row in rows],
        # The count the display was built from. Not recomputed from the rows —
        # this is how many the display holds, which is what a reader needs to
        # know when only some are printed.
        total_row_count=len(chart.data),
    )


def _metric_of(item: KPIItem, chart: ChartSpec) -> CompiledMetric:
    """Carry one headline figure and whatever provenance the run recorded.

    The display string is the run's. Nothing here formats a raw value into one
    or parses one out of the other.
    """

    query_ids = [item.source_query_id] if item.source_query_id else list(chart.source_query_ids)
    return CompiledMetric(
        label=item.label,
        display_value=item.value,
        raw_value=item.raw_value,
        change=item.change,
        source_query_ids=query_ids[:12],
        source_column=item.source_column,
        row_selector=RowSelector(fields=dict(item.row_selector)) if item.row_selector else None,
    )


def _scope_rows(
    *, run_id: str, generated_at: datetime, period: str | None,
    sources: list[AnswerSource], charts: list[ChartSpec], tables: list[ChartSpec],
) -> list[ScopeRow]:
    """State the scope a reader would otherwise have to infer."""

    consulted = sorted({table for source in sources for table in source.referenced_tables})
    rows = [
        ScopeRow(label="Generated", value=generated_at.strftime("%d %B %Y, %H:%M UTC")),
    ]
    if period:
        rows.append(ScopeRow(label="Period covered", value=period))
    # len() over a list the run produced is a count of evidence items, not a
    # calculation over data. No figure in the report is derived from it.
    rows.append(ScopeRow(label="Queries executed", value=str(len(sources))))
    if consulted:
        rows.append(ScopeRow(label="Tables consulted", value=", ".join(consulted)))
    rows.append(ScopeRow(
        label="Displays included",
        value=f"{_plural(len(charts), 'chart')}, {_plural(len(tables), 'table')}",
    ))
    rows.append(ScopeRow(label="Run reference", value=run_id))
    return rows


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _evidence(
    sources: list[AnswerSource], blocks: list[ReportBlock], period: str | None,
) -> list[EvidenceEntry]:
    """Account for every query the report rests on, and what it contributed.

    Everything here was recorded by the runtime when the query ran; the only
    thing derived is which figures cite it, which the compiler knows because it
    just laid them out.
    """

    displayed: dict[str, dict[str, CompiledRows]] = {}
    used_by: dict[str, list[str]] = {}
    for block in blocks:
        label = getattr(block, "figure_label", None)
        for query_id in getattr(block, "source_query_ids", ()) or ():
            if label:
                used_by.setdefault(query_id, []).append(label)
                displayed.setdefault(query_id, {})[label] = getattr(block, "data", CompiledRows())
        for metric in getattr(block, "metrics", ()) or ():
            for query_id in metric.source_query_ids:
                used_by.setdefault(query_id, []).append(metric.label)

    return [
        EvidenceEntry(
            query_id=source.id,
            description=source.label,
            executed_at=source.executed_at,
            period=period,
            tables_consulted=list(source.referenced_tables),
            returned_columns=list(source.columns),
            row_count=source.row_count,
            truncated=source.truncated,
            displayed_rows=displayed.get(source.id, {}),
            used_by=used_by.get(source.id, [])[:24],
        )
        for source in sources
    ]


def _has_content(kind: str, *, narrative, metrics, charts, tables, caveats, notices, sources) -> bool:
    """Whether a block has anything to show, so empty headings are dropped."""

    return bool({
        "cover": True,
        "narrative": narrative,
        "metrics": metrics,
        "chart": charts,
        "table": tables,
        "caveats": caveats or notices,
        "scope": True,
        "evidence": sources,
        "page_break": True,
    }.get(kind))


def compile_report(
    *,
    template: ReportTemplate,
    run_id: str,
    answer: str,
    charts: Iterable[ChartSpec],
    sources: Iterable[AnswerSource],
    generated_at: datetime,
    period: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    caveats: Iterable[str] | None = None,
    report_id: str | None = None,
    narrative_status: NarrativeStatus = "current",
    analysis_period: str | None = None,
    content_order: dict[str, list[str]] | None = None,
) -> CompiledReport:
    """Lay one run out as the template asks, without changing what it says.

    ``period`` is what the figures describe. ``analysis_period`` is what the
    prose was written for; when they differ the narrative is either dropped or
    kept under a warning, according to ``narrative_status``. It is never
    silently reused.

    ``content_order``, when given, names the chart ids each block kind should
    draw from and in what order — the output of
    ``app.analytics.presentation.assignment.TemplateAssignment.content_order``.
    Absent, the block still takes every matching chart in the order it was
    given, exactly as before slots existed; this keeps every existing caller
    unaffected.
    """

    all_charts = list(charts)
    resolved = list(sources)
    stated = list(caveats or ())
    chart_by_id = {chart.id: chart for chart in all_charts}

    def _ordered(block_kind: str) -> list[ChartSpec]:
        if content_order is None:
            return all_charts
        return [chart_by_id[chart_id] for chart_id in content_order.get(block_kind, []) if chart_id in chart_by_id]

    drawable = [chart for chart in _ordered("chart") if chart.type in RASTERIZABLE]
    grids = [chart for chart in _ordered("table") if chart.type == "table"]
    headline = [(item, chart) for chart in _ordered("metrics") if chart.type == "kpi" for item in chart.kpis]
    written_for = analysis_period if analysis_period is not None else period
    excluded = narrative_status == "excluded_from_refreshed_report"
    narrative = [] if excluded else parse_prose(answer or "")
    warning = narrative_warning(narrative_status, written_for, period)
    notices = [CITATION_NOTICE] if resolved else []
    document_title = title or template.title

    blocks: list[ReportBlock] = []
    figure_number = 0
    table_number = 0

    for spec in template.blocks:
        present = _has_content(
            spec.kind, narrative=narrative, metrics=headline, charts=drawable,
            tables=grids, caveats=stated, notices=notices, sources=resolved,
        )
        if not present and not spec.required:
            continue

        if spec.kind == "cover":
            blocks.append(CoverBlock(
                title=document_title, subtitle=subtitle, period=period, generated_at=generated_at,
            ))
        elif spec.kind == "page_break":
            blocks.append(PageBreakBlock())
        elif spec.kind == "narrative":
            blocks.append(NarrativeBlock(
                heading=spec.heading, lines=narrative[:400], warning=warning,
                empty_message=(
                    "The written narrative was left out because the figures in this "
                    "report were recomputed for a different period."
                    if excluded else "This run produced no written answer."
                ),
            ))
        elif spec.kind == "metrics":
            selected = headline if spec.limit is None else headline[: spec.limit]
            blocks.append(MetricsBlock(
                heading=spec.heading,
                metrics=[_metric_of(item, chart) for item, chart in selected],
            ))
        elif spec.kind == "chart":
            for chart in (drawable if spec.limit is None else drawable[: spec.limit]):
                figure_number += 1
                blocks.append(ChartBlock(
                    heading=spec.heading if figure_number == 1 else None,
                    chart_id=chart.id, title=chart.title,
                    figure_label=f"Figure {figure_number}", chart_type=chart.type,
                    caption=chart.description, source_query_ids=list(chart.source_query_ids),
                    data=_rows_of(chart), formatting=chart.formatting, period=period,
                ))
            if not drawable:
                # A required section that has nothing to show says so, rather
                # than inventing a figure to fill itself with.
                blocks.append(NarrativeBlock(
                    heading=spec.heading,
                    empty_message="This analysis produced no charts.",
                ))
        elif spec.kind == "table":
            for chart in (grids if spec.limit is None else grids[: spec.limit]):
                table_number += 1
                blocks.append(TableBlock(
                    heading=spec.heading if table_number == 1 else None,
                    table_id=chart.id, title=chart.title,
                    figure_label=f"Table {table_number}",
                    source_query_ids=list(chart.source_query_ids),
                    data=_rows_of(chart, limit=MAX_DOCUMENT_TABLE_ROWS), period=period,
                ))
            if not grids:
                blocks.append(NarrativeBlock(
                    heading=spec.heading,
                    empty_message="This analysis produced no data tables.",
                ))
        elif spec.kind == "caveats":
            blocks.append(CaveatsBlock(
                heading=spec.heading, stated=stated[:10], system_notices=notices,
            ))
        elif spec.kind == "scope":
            blocks.append(ScopeBlock(heading=spec.heading, rows=_scope_rows(
                run_id=run_id, generated_at=generated_at, period=period,
                sources=resolved, charts=drawable, tables=grids,
            )))
        elif spec.kind == "evidence":
            blocks.append(EvidenceBlock(
                heading=spec.heading,
                entries=_evidence(resolved, blocks, period),
                note="Each citation names a query this run executed.",
            ))

    return CompiledReport(
        report_id=report_id or str(uuid4()),
        run_id=run_id,
        title=document_title,
        subtitle=subtitle,
        template_id=template.name,
        template_version=template.version,
        analysis_period=written_for,
        displayed_period=period,
        narrative_period_status=narrative_status,
        narrative_warning=warning,
        orientation=template.orientation,
        blocks=blocks,
        sources=resolved,
        generated_at=generated_at,
    )
