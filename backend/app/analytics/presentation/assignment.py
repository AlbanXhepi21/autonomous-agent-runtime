"""Deterministic assignment of a run's displays into a template's content slots.

A completed run already holds every display it will ever have — nothing here
creates one, changes what it says, or asks a model for an opinion about it.
Assignment only decides, given a template's declared slots and a run's
displays in the order they were created, which display (if any) goes in each
slot. The same inputs always produce the same output, which is what lets a
preview and the report it later publishes be provably the same assignment.

What this module may do: read a display's type, title and description, its
position in creation order, and which of its cited queries the run's resolved
evidence actually contains. What it may not do: compute a new figure, invent a
display, or let one display fill two slots.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.presentation.charts import ChartSpec
from app.analytics.presentation.document_model import BlockKind
from app.analytics.presentation.templates import ReportTemplate, TemplateSlot
from app.contracts.answers import AnswerSource


class SlotAssignment(BaseModel):
    """What one slot ended up with, and whether that was enough."""

    model_config = ConfigDict(extra="forbid")

    slot_id: str
    accepts: list[str]
    block_kind: BlockKind
    role: Literal["primary", "supporting"]
    required: bool
    minimum: int
    maximum: int
    #: Chart ids assigned to this slot, in the run's original creation order —
    #: never in the order a purpose hint happened to rank them.
    assigned_chart_ids: list[str] = Field(default_factory=list)
    satisfied: bool


class TemplateAssignment(BaseModel):
    """The complete, deterministic result of fitting one run to one template."""

    model_config = ConfigDict(extra="forbid")

    template_name: str
    slots: list[SlotAssignment] = Field(default_factory=list)
    #: Displays no slot claimed — not missing content, just content this
    #: template's plan does not call for.
    unused_chart_ids: list[str] = Field(default_factory=list)
    #: Displays excluded from every slot because at least one query id they
    #: cite is not part of this run's resolved evidence. Never assigned and
    #: never counted as merely "unused", since offering them anywhere would
    #: print a figure the report cannot account for.
    unresolved_evidence_chart_ids: list[str] = Field(default_factory=list)

    def content_order(self) -> dict[BlockKind, list[str]]:
        """Chart ids per document block, in slot-priority then creation order.

        This is the only thing the compiler needs from an assignment: which
        ids to use, and in what order, for each block kind a slot feeds.
        """

        order: dict[BlockKind, list[str]] = {}
        for slot in self.slots:
            bucket = order.setdefault(slot.block_kind, [])
            bucket.extend(chart_id for chart_id in slot.assigned_chart_ids if chart_id not in bucket)
        return order


def _purpose_rank(chart: ChartSpec, slot: TemplateSlot) -> int:
    """0 when a slot's purpose hint appears in the display; 1 otherwise.

    A pure preference between two otherwise-eligible displays. A display's
    title and description are exactly what its creator wrote; nothing here
    reads, alters, or reasons about anything beyond that stated text.
    """

    hint = (slot.purpose_hint or "").strip().casefold()
    if not hint:
        return 0
    haystack = f"{chart.title} {chart.description or ''}".casefold()
    return 0 if hint in haystack else 1


def _unit_count(chart: ChartSpec) -> int:
    """How much of a slot's minimum/maximum one display is worth.

    A "kpi" display's individual figures are what a metrics block actually
    prints — the same granularity the compiler's own block ``limit`` already
    counts in — so a single kpi display carrying four headline figures alone
    satisfies a "needs three headline metrics" slot. Every other display
    counts as one unit, matching the one chart or one table the chart/table
    block prints for it. A display's units are never split across slots.
    """

    return len(chart.kpis) if chart.type == "kpi" else 1


def assign_slots(
    template: ReportTemplate, charts: Sequence[ChartSpec], sources: Sequence[AnswerSource]
) -> TemplateAssignment:
    """Fit one run's displays to one template's slots, deterministically.

    Slots are filled in the template's own declared order — a template states
    its priorities by how it lists its slots, not by any property assignment
    infers on its own. Within a slot, an eligible display already matching its
    purpose hint is preferred; ties, and every slot with no hint, fall back to
    the display's original creation order. Candidates are then taken in that
    order while they fit the slot's maximum, except that the first candidate
    is always taken whole even if its own units exceed the maximum alone —
    a display is never split to fit. A display placed in a slot is removed
    from consideration for every slot that follows, so nothing is ever
    duplicated to fill space.
    """

    known_query_ids = {source.id for source in sources}
    eligible: list[ChartSpec] = []
    unresolved_evidence_chart_ids: list[str] = []
    for chart in charts:
        if set(chart.source_query_ids) <= known_query_ids:
            eligible.append(chart)
        else:
            unresolved_evidence_chart_ids.append(chart.id)

    creation_index = {chart.id: index for index, chart in enumerate(eligible)}
    available = list(eligible)

    slot_assignments: list[SlotAssignment] = []
    for slot in template.slots:
        candidates = [chart for chart in available if chart.type in slot.accepts]
        ranked = sorted(candidates, key=lambda chart: (_purpose_rank(chart, slot), creation_index[chart.id]))

        selected: list[ChartSpec] = []
        units = 0
        for chart in ranked:
            chart_units = _unit_count(chart)
            if units and units + chart_units > slot.maximum:
                break
            selected.append(chart)
            units += chart_units
            if units >= slot.maximum:
                break

        selected = sorted(selected, key=lambda chart: creation_index[chart.id])
        selected_ids = {chart.id for chart in selected}
        available = [chart for chart in available if chart.id not in selected_ids]
        slot_assignments.append(SlotAssignment(
            slot_id=slot.id, accepts=list(slot.accepts), block_kind=slot.block_kind, role=slot.role,
            required=slot.required, minimum=slot.minimum, maximum=slot.maximum,
            assigned_chart_ids=[chart.id for chart in selected],
            satisfied=units >= slot.minimum,
        ))

    return TemplateAssignment(
        template_name=template.name, slots=slot_assignments,
        unused_chart_ids=[chart.id for chart in available],
        unresolved_evidence_chart_ids=unresolved_evidence_chart_ids,
    )
