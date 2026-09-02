"""A deterministic, pre-publish view of what a report will actually contain.

A preview compiles the exact same ``CompiledReport`` a publish would produce —
same template, same assignment, same figures — without writing a PDF or DOCX
file. It exists so a reader can see what a template will do with a run's
displays, and see what is missing, before spending a render on it.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict

from app.analytics.presentation.assignment import TemplateAssignment
from app.analytics.presentation.document_model import CompiledReport
from app.analytics.presentation.suitability import TemplateSuitability
from app.analytics.presentation.templates import ReportTemplate

#: A PDF is generated from the same compiled report a preview shows, but text
#: reflow, page breaks and font metrics are decided by the PDF writer, not by
#: this preview. The PDF is the record; a DOCX copy is provided for editing
#: and stops being that record the moment it is edited.
PDF_AUTHORITATIVE_NOTICE = (
    "This preview is generated for review only. The published PDF is the authoritative record "
    "of this report's figures and layout. A Word copy is provided for editing and reuse; once "
    "edited it is no longer a record of what this run produced."
)

#: Rough content units a page holds, used only to size a preview estimate.
#: Not a layout simulation — the PDF writer's own pagination is authoritative,
#: this exists only to tell a reader "about how long", not to predict it.
_UNITS_PER_PAGE = 7.0
_BLOCK_UNITS = {"cover": 4.0, "scope": 1.0, "narrative": 1.0, "metrics": 1.0,
                "chart": 3.0, "table": 2.0, "caveats": 1.0, "evidence": 1.0, "page_break": 0.0}
_PER_ITEM_UNITS = {"scope": 0.3, "narrative": 0.5, "metrics": 0.4, "table": 0.15,
                    "caveats": 0.3, "evidence": 0.3}


def estimate_page_count(report: CompiledReport) -> int:
    """A safe, clearly-approximate page count from simple content counts.

    Each block contributes a fixed base plus a small amount per item it
    holds (a narrative line, a metric, a table row, an evidence entry); the
    total is divided by a fixed units-per-page constant and rounded up. This
    deliberately ignores font metrics, margins and text reflow — the one
    thing it must never do is claim precision the renderer alone can provide.
    """

    units = 0.0
    for block in report.blocks:
        units += _BLOCK_UNITS.get(block.kind, 1.0)
        per_item = _PER_ITEM_UNITS.get(block.kind)
        if per_item is None:
            continue
        if block.kind == "scope":
            units += per_item * len(block.rows)
        elif block.kind == "narrative":
            units += per_item * len(block.lines)
        elif block.kind == "metrics":
            units += per_item * len(block.metrics)
        elif block.kind == "table":
            units += per_item * len(block.data.rows)
        elif block.kind == "caveats":
            units += per_item * (len(block.stated) + len(block.system_notices))
        elif block.kind == "evidence":
            units += per_item * len(block.entries)
    return max(1, math.ceil(units / _UNITS_PER_PAGE))


def missing_required_content(template: ReportTemplate, assignment: TemplateAssignment) -> list[str]:
    """Plain-language statements of what a required slot still needs.

    Stated instead of silently leaving the slot empty, so a reader sees
    exactly what content is missing rather than a report that looks finished
    but is not.
    """

    by_id = {slot.id: slot for slot in template.slots}
    messages: list[str] = []
    for outcome in assignment.slots:
        if not outcome.required or outcome.satisfied:
            continue
        slot = by_id.get(outcome.slot_id)
        kinds = ", ".join(outcome.accepts) if slot is None else ", ".join(slot.accepts)
        have = len(outcome.assigned_chart_ids)
        messages.append(
            f"'{outcome.slot_id}' needs at least {outcome.minimum} display(s) of type "
            f"{kinds}, but only {have} {'is' if have == 1 else 'are'} available."
        )
    return messages


class ReportPreview(BaseModel):
    """Everything a reader needs to judge a report before it is published."""

    model_config = ConfigDict(extra="forbid")

    template_name: str
    template_title: str
    report: CompiledReport
    suitability: TemplateSuitability
    assignment: TemplateAssignment
    missing_required_content: list[str]
    estimated_page_count: int
    pdf_authoritative_notice: str = PDF_AUTHORITATIVE_NOTICE


class TemplateSuitabilityOverview(BaseModel):
    """Every template's fit for one run, and which one best fits it."""

    model_config = ConfigDict(extra="forbid")

    items: list[TemplateSuitability]
    recommended_template: str | None = None
