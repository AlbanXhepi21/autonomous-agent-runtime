"""Deterministic suitability scoring for one template assignment.

Scoring formula
----------------
``completion_percentage`` is 100.0 when a template declares no required
slots. Otherwise it is::

    100.0 * (required slots satisfied) / (required slots total)

rounded to one decimal place. A slot is "satisfied" once
``assign_slots`` gave it at least its declared minimum — see
``app.analytics.presentation.assignment``. Nothing else feeds this number:
optional content and unused displays never raise or lower it, because a
template's fitness is judged on whether it can honestly carry the content it
requires, not on how much of a run it happens to use.

``can_publish`` is exactly ``not missing_required_slots`` — publication is
never blocked by an optional gap or an unused display, only by a slot the
template itself declared essential.

Recommendation ranks templates by, in order:

1. ``completion_percentage``, descending — closest to a complete report.
2. ``optional_slots_filled``, descending — prefers using more of what a run
   actually created when two templates are equally complete.
3. ``unused_display_count``, ascending — prefers wasting less of it.
4. ``template_name``, ascending — a final, arbitrary but stable tiebreak so
   the result never depends on dictionary or set ordering.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from app.analytics.presentation.assignment import TemplateAssignment


class TemplateSuitability(BaseModel):
    """How well one template fits the content a run actually produced."""

    model_config = ConfigDict(extra="forbid")

    template_name: str
    completion_percentage: float
    satisfied_required_slots: list[str]
    missing_required_slots: list[str]
    optional_slots_filled: int
    optional_slots_total: int
    unused_display_count: int
    warnings: list[str]
    can_publish: bool


def score_assignment(assignment: TemplateAssignment) -> TemplateSuitability:
    """Score one template's fit from its already-computed assignment."""

    required = [slot for slot in assignment.slots if slot.required]
    optional = [slot for slot in assignment.slots if not slot.required]
    satisfied_required = [slot.slot_id for slot in required if slot.satisfied]
    missing_required = [slot.slot_id for slot in required if not slot.satisfied]
    optional_filled = [slot.slot_id for slot in optional if slot.assigned_chart_ids]
    completion = 100.0 if not required else round(100.0 * len(satisfied_required) / len(required), 1)

    warnings: list[str] = []
    if assignment.unused_chart_ids:
        warnings.append(
            f"{len(assignment.unused_chart_ids)} display(s) created during the run are not used by this template."
        )
    if assignment.unresolved_evidence_chart_ids:
        warnings.append(
            f"{len(assignment.unresolved_evidence_chart_ids)} display(s) were excluded because they cite "
            "evidence outside this run's resolved citations."
        )
    for slot in optional:
        if slot.minimum > 0 and not slot.satisfied:
            warnings.append(
                f"Optional slot '{slot.slot_id}' wanted at least {slot.minimum} display(s) "
                f"but has {len(slot.assigned_chart_ids)}."
            )

    return TemplateSuitability(
        template_name=assignment.template_name, completion_percentage=completion,
        satisfied_required_slots=satisfied_required, missing_required_slots=missing_required,
        optional_slots_filled=len(optional_filled), optional_slots_total=len(optional),
        unused_display_count=len(assignment.unused_chart_ids), warnings=warnings,
        can_publish=not missing_required,
    )


def recommend_template(suitabilities: Sequence[TemplateSuitability]) -> str | None:
    """The best-fitting template name by the documented ranking, or None."""

    if not suitabilities:
        return None
    ranked = sorted(
        suitabilities,
        key=lambda item: (
            -item.completion_percentage, -item.optional_slots_filled,
            item.unused_display_count, item.template_name,
        ),
    )
    return ranked[0].template_name
