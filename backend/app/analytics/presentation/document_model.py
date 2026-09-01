"""The compiled report: one canonical document both renderers read.

A report is compiled once, from a run that already happened, into the model
below. The PDF writer and the DOCX writer then walk the same blocks in the same
order. Neither decides what to include, which figures to print or which queries
to cite — if they disagree about a fact, that is a bug in the compiler rather
than a difference of opinion between two renderers.

The model is deliberately inert. Every number it holds was produced by a query
during the run and is carried here verbatim alongside where it came from;
nothing in this module or in either renderer sums, averages, counts, computes a
percentage or fills in a missing value. Presentation may filter rows, reorder
them, relabel a column and format a value it was given — that is the whole of
what it may do.

Blocks form a discriminated union on ``kind`` so a renderer handles the closed
set exhaustively and an unknown block cannot reach a document silently.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.presentation.charts import ChartFormatting, ChartType
from app.contracts.answers import AnswerSource

#: What a block is. A renderer must handle every member.
BlockKind = Literal[
    "cover", "scope", "narrative", "metrics", "chart",
    "table", "caveats", "evidence", "page_break",
]

ProseKind = Literal["heading", "paragraph", "bullet", "number"]

#: Whether the written narrative still describes the figures printed beside it.
#:
#: ``current`` — the prose and the numbers come from the same run and period.
#: ``pinned_to_original_period`` — figures were recomputed for a different
#: period and the prose was kept anyway, at the reader's request. It describes
#: the original period and says so, loudly, wherever it appears.
#: ``excluded_from_refreshed_report`` — figures were recomputed and the prose
#: was left out rather than allowed to describe data it never saw.
#:
#: There is deliberately no state in which prose silently describes refreshed
#: numbers. Rewriting it would need a model, and publishing never calls one.
NarrativeStatus = Literal["current", "pinned_to_original_period", "excluded_from_refreshed_report"]

#: The previous name, kept so existing readers of the field still resolve.
NarrativePeriodStatus = NarrativeStatus


#: What a query cell may hold once serialized. Deliberately narrow: a document
#: prints values, never structures.
CellValue = str | int | float | bool | None


class RowSelector(BaseModel):
    """Which row a figure was read out of, by identity rather than by position.

    An index would stop meaning the same row the moment a display is filtered or
    reordered, both of which presentation is allowed to do. Naming the cells
    that identify the row survives that.
    """

    model_config = ConfigDict(extra="forbid")

    fields: dict[str, CellValue] = Field(default_factory=dict, max_length=8)

    def describe(self) -> str:
        return ", ".join(f"{key}={value}" for key, value in self.fields.items())


class CompiledMetric(BaseModel):
    """One headline figure, with the cell it was read from.

    ``raw_value`` is what the query returned and ``display_value`` is how it is
    printed. The compiler never produces one from the other in either direction:
    a run supplies both, or supplies only the display string and the raw value
    stays absent.
    """

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=120)
    display_value: str = Field(min_length=1, max_length=120)
    #: The unformatted value behind ``display_value``, when the run recorded it.
    raw_value: float | int | str | None = None
    change: str | None = Field(default=None, max_length=120)
    source_query_ids: list[str] = Field(default_factory=list, max_length=12)
    source_column: str | None = Field(default=None, max_length=80)
    row_selector: RowSelector | None = None

    @property
    def provenance_is_complete(self) -> bool:
        """Whether this figure can be traced to an exact cell of an exact query."""

        return bool(self.source_query_ids and self.source_column and self.row_selector)


class CompiledRows(BaseModel):
    """The exact rows a figure was drawn from, after filtering and ordering.

    These are the rows the document shows, not the rows the query returned:
    presentation may narrow and reorder, and the appendix has to restate what
    was actually printed rather than what was available.
    """

    model_config = ConfigDict(extra="forbid")

    columns: list[str] = Field(default_factory=list, max_length=32)
    rows: list[dict[str, CellValue]] = Field(default_factory=list, max_length=500)
    #: Rows the source query returned, when that is larger than what is shown.
    total_row_count: int | None = Field(default=None, ge=0)

    @property
    def is_truncated(self) -> bool:
        return self.total_row_count is not None and self.total_row_count > len(self.rows)


class ProseLine(BaseModel):
    """One paragraph-level piece of the written answer."""

    model_config = ConfigDict(extra="forbid")

    kind: ProseKind
    text: str = Field(min_length=1, max_length=8_000)
    level: int = Field(default=0, ge=0, le=6)


# --------------------------------------------------------------------- blocks


class _Block(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #: Printed as the section heading. Absent for blocks that carry no heading.
    heading: str | None = Field(default=None, max_length=160)


class CoverBlock(_Block):
    """Title page material. Carries no facts of its own."""

    kind: Literal["cover"] = "cover"
    title: str = Field(min_length=1, max_length=200)
    subtitle: str | None = Field(default=None, max_length=300)
    period: str | None = Field(default=None, max_length=160)
    generated_at: datetime


class ScopeRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=120)
    value: str = Field(max_length=2_000)


class ScopeBlock(_Block):
    """What the report covers, stated so a reader need not infer it."""

    kind: Literal["scope"] = "scope"
    rows: list[ScopeRow] = Field(default_factory=list, max_length=24)


class NarrativeBlock(_Block):
    """The analyst's written answer, as document lines rather than as Markdown."""

    kind: Literal["narrative"] = "narrative"
    lines: list[ProseLine] = Field(default_factory=list, max_length=400)
    #: Printed above the prose when it describes a different period from the
    #: figures. Carried on the block so no renderer can forget to show it.
    warning: str | None = Field(default=None, max_length=500)
    #: Printed when the run produced no written answer, so the section is never
    #: silently empty.
    empty_message: str = Field(default="This run produced no written answer.", max_length=300)


class MetricsBlock(_Block):
    """Headline figures, each carrying the query cell it was read from."""

    kind: Literal["metrics"] = "metrics"
    metrics: list[CompiledMetric] = Field(default_factory=list, max_length=12)
    empty_message: str = Field(default="This analysis produced no headline metrics.", max_length=300)


class ChartBlock(_Block):
    """One drawn figure and the rows it was drawn from."""

    kind: Literal["chart"] = "chart"
    #: Matches the key of the rendered image handed to a renderer.
    chart_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    #: Stable label a reader and the appendix both use, such as "Figure 2".
    figure_label: str = Field(min_length=1, max_length=40)
    chart_type: ChartType
    caption: str | None = Field(default=None, max_length=500)
    source_query_ids: list[str] = Field(default_factory=list, max_length=12)
    data: CompiledRows = Field(default_factory=CompiledRows)
    formatting: ChartFormatting = Field(default_factory=ChartFormatting)
    #: The period these rows describe, carried from the report.
    period: str | None = Field(default=None, max_length=160)


class TableBlock(_Block):
    """A grid of exact values, printed rather than summarised."""

    kind: Literal["table"] = "table"
    table_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    figure_label: str = Field(min_length=1, max_length=40)
    source_query_ids: list[str] = Field(default_factory=list, max_length=12)
    data: CompiledRows = Field(default_factory=CompiledRows)
    period: str | None = Field(default=None, max_length=160)
    empty_message: str = Field(default="This analysis produced no data tables.", max_length=300)


class CaveatsBlock(_Block):
    """Limitations, kept in two lists that must not be confused for each other.

    ``stated`` was written by the analysis about itself. ``system_notices`` hold
    for any report of this shape and are supplied by the runtime.
    """

    kind: Literal["caveats"] = "caveats"
    stated: list[str] = Field(default_factory=list, max_length=10)
    system_notices: list[str] = Field(default_factory=list, max_length=4)
    empty_message: str = Field(default="This analysis stated no limitations.", max_length=300)


class EvidenceEntry(BaseModel):
    """One query, as the appendix accounts for it.

    Everything here was recorded by the runtime when the query ran, or derived
    by the compiler from which blocks cite it. The model never authors an
    evidence record.
    """

    model_config = ConfigDict(extra="forbid")

    query_id: str = Field(min_length=1, max_length=80)
    #: The runtime's description of what was asked, from the query's purpose.
    description: str = Field(min_length=1, max_length=300)
    executed_at: datetime | None = None
    period: str | None = Field(default=None, max_length=160)
    #: Parameters the runtime recorded for this query, when it recorded any.
    parameters: dict[str, CellValue] = Field(default_factory=dict, max_length=16)
    tables_consulted: list[str] = Field(default_factory=list, max_length=16)
    returned_columns: list[str] = Field(default_factory=list, max_length=32)
    #: Present when this evidence came from a recompiled metric rather than
    #: from SQL the agent wrote.
    metric: str | None = Field(default=None, max_length=64)
    dimensions: list[str] = Field(default_factory=list, max_length=4)
    sql_fingerprint: str | None = Field(default=None, max_length=64)
    row_count: int | None = Field(default=None, ge=0)
    truncated: bool = False
    #: The rows this report actually printed from the query, per figure.
    displayed_rows: dict[str, CompiledRows] = Field(default_factory=dict, max_length=16)
    #: Figures and sections resting on this query, by their printed labels.
    used_by: list[str] = Field(default_factory=list, max_length=24)


class EvidenceBlock(_Block):
    """The appendix: every query the report used, and what it contributed."""

    kind: Literal["evidence"] = "evidence"
    entries: list[EvidenceEntry] = Field(default_factory=list, max_length=64)
    note: str | None = Field(default=None, max_length=400)
    empty_message: str = Field(default="This report cites no queried evidence.", max_length=300)


class PageBreakBlock(_Block):
    """An explicit break. Renderers honour it; nothing else depends on it."""

    kind: Literal["page_break"] = "page_break"


ReportBlock = Annotated[
    CoverBlock | ScopeBlock | NarrativeBlock | MetricsBlock
    | ChartBlock | TableBlock | CaveatsBlock | EvidenceBlock | PageBreakBlock,
    Field(discriminator="kind"),
]


# -------------------------------------------------------------------- document


class CompiledReport(BaseModel):
    """One report, compiled and ready to render in any supported format."""

    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(min_length=1, max_length=80)
    run_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=200)
    subtitle: str | None = Field(default=None, max_length=300)
    template_id: str = Field(min_length=1, max_length=64)
    template_version: str = Field(min_length=1, max_length=32)
    #: The period the analysis covered, as supplied when publishing.
    analysis_period: str | None = Field(default=None, max_length=160)
    #: The period the document presents. Equal to ``analysis_period`` while
    #: figures are never refreshed independently of the narrative.
    displayed_period: str | None = Field(default=None, max_length=160)
    narrative_period_status: NarrativeStatus = "current"
    #: Printed wherever the narrative appears when it no longer describes the
    #: figures beside it. Empty while the two agree.
    narrative_warning: str | None = Field(default=None, max_length=500)
    orientation: Literal["portrait", "landscape"] = "portrait"
    blocks: list[ReportBlock] = Field(default_factory=list, max_length=64)
    #: The evidence registry the run resolved. Unknown identifiers were already
    #: dropped upstream, so anything here names a query that actually ran.
    sources: list[AnswerSource] = Field(default_factory=list, max_length=64)
    generated_at: datetime

    def blocks_of(self, kind: BlockKind) -> list[Any]:
        """Return the blocks of one kind, in document order."""

        return [block for block in self.blocks if block.kind == kind]

    @property
    def cited_query_ids(self) -> list[str]:
        """Every query identifier the compiled blocks rest on, in order."""

        seen: list[str] = []
        for block in self.blocks:
            for query_id in getattr(block, "source_query_ids", ()) or ():
                if query_id not in seen:
                    seen.append(query_id)
            for metric in getattr(block, "metrics", ()) or ():
                for query_id in metric.source_query_ids:
                    if query_id not in seen:
                        seen.append(query_id)
        return seen
