"""Document structures a finished analysis can be published into.

A template says what a deliverable contains and in what order — not what it
measures. The numbers, charts and citations come from a run that already
happened, so publishing one is a deterministic assembly step rather than
another turn of the agent.

Templates are content, not code: they live beside the skills and specialists in
``app/resources`` so a new report shape is a JSON file rather than a release.
Each directory holds two files with two different jobs — ``metadata.json`` for
structure and ``theme.json`` for appearance — because a house restyle and a new
section are not the same change and should not be able to break each other.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.analytics.presentation.charts import PLOTTED_TYPES, ChartType
from app.analytics.presentation.document_model import BlockKind
from app.analytics.presentation.reports import ReportType
from app.analytics.presentation.theme import DEFAULT_THEME, ReportTheme
from app.resources import resources_path

PeriodGranularity = Literal["month", "quarter", "year", "custom"]
Orientation = Literal["portrait", "landscape"]
DocumentFormat = Literal["pdf", "docx"]


def _all_formats() -> list[DocumentFormat]:
    """Every format a template supports unless it narrows the list itself."""

    return ["pdf", "docx"]


class ReportTemplateError(Exception):
    """Raised when a template definition on disk cannot be trusted."""


class TemplateBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: BlockKind
    #: Absent for structural blocks such as a page break, which print nothing.
    heading: str | None = Field(default=None, min_length=1, max_length=120)
    #: Blocks with nothing to show are dropped rather than printed empty,
    #: unless the deliverable is expected to account for their absence.
    required: bool = False
    #: The most items this block may print — four charts on a dashboard, say.
    #: The compiler takes the first ``limit`` and records that it did; it never
    #: chooses which are most interesting, because that would be a judgement
    #: about the analysis rather than about the page.
    limit: int | None = Field(default=None, ge=1, le=100)

    @model_validator(mode="after")
    def require_a_heading_where_one_is_printed(self) -> TemplateBlock:
        if self.kind not in {"page_break", "cover"} and not self.heading:
            raise ValueError(f"A {self.kind} block needs a heading.")
        return self


#: The three families a slot's accepted display types may belong to. A slot
#: mixing families (say, a "kpi" alongside a "table") would leave the
#: assignment step unable to say which document block it feeds, so each slot
#: must live entirely within one.
_SLOT_KIND_FAMILIES: tuple[frozenset[str], ...] = (frozenset({"kpi"}), frozenset({"table"}), PLOTTED_TYPES)


class TemplateSlot(BaseModel):
    """One deliberate place in a template for a specific kind of content.

    A slot is how a template states what it needs — not what any particular
    run happens to have. ``app.analytics.presentation.assignment`` reads these
    to decide, deterministically, which of a run's already-created displays
    goes where; nothing about a slot causes new content to be computed.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    #: The display types this slot may hold, matching ``ChartSpec.type``.
    accepts: list[ChartType] = Field(min_length=1, max_length=8)
    minimum: int = Field(default=0, ge=0, le=12)
    maximum: int = Field(default=1, ge=1, le=12)
    required: bool = False
    #: Whether this slot carries the template's principal content or content
    #: that merely supports it. Purely descriptive — it does not change
    #: assignment, only how a reader and the suitability warnings describe it.
    role: Literal["primary", "supporting"] = "primary"
    #: Checked case-insensitively against a candidate display's title and
    #: description to prefer one already-created display over another for
    #: this slot. Never used to accept a display that fails ``accepts``, and
    #: never used to alter or invent what a display says.
    purpose_hint: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _validate(self) -> TemplateSlot:
        if self.minimum > self.maximum:
            raise ValueError(f"Slot {self.id}: minimum cannot exceed maximum.")
        if self.required and self.minimum < 1:
            raise ValueError(f"Slot {self.id}: a required slot needs a minimum of at least 1.")
        kinds = frozenset(self.accepts)
        if len(kinds) != len(self.accepts):
            raise ValueError(f"Slot {self.id}: accepts must not repeat a display type.")
        if not any(kinds <= family for family in _SLOT_KIND_FAMILIES):
            raise ValueError(
                f"Slot {self.id}: accepts must stay within one family — "
                "kpi, table, or the plotted chart types — never mixed."
            )
        return self

    @property
    def block_kind(self) -> BlockKind:
        """Which document block a display assigned to this slot feeds."""

        if "kpi" in self.accepts:
            return "metrics"
        if "table" in self.accepts:
            return "table"
        return "chart"


class ReportTemplate(BaseModel):
    """One publishable document shape."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    #: Bumped by hand when a template's blocks change, so a published artifact
    #: records the shape it was written from rather than the shape that happens
    #: to be on disk when someone re-reads it. Absent means the first version.
    version: str = Field(default="1", min_length=1, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=400)
    report_type: ReportType
    period_granularity: PeriodGranularity
    orientation: Orientation = "portrait"
    #: The formats this shape is meant to be produced in. A landscape dashboard
    #: may reasonably decline DOCX rather than render badly in it.
    formats: list[DocumentFormat] = Field(default_factory=_all_formats, min_length=1)
    blocks: list[TemplateBlock] = Field(min_length=1, max_length=24)
    #: Deterministic content slots, in priority order: earlier slots claim a
    #: matching display before later ones. Empty means this template's
    #: "chart"/"table"/"metrics" blocks take a run's displays directly, in
    #: creation order, exactly as before slots existed.
    slots: list[TemplateSlot] = Field(default_factory=list, max_length=16)
    #: Populated from the directory's ``theme.json``; not part of the structure
    #: file, so a restyle never edits the section list.
    theme: ReportTheme = Field(default_factory=lambda: DEFAULT_THEME)

    def supports(self, document_format: str) -> bool:
        return document_format in self.formats

    @model_validator(mode="after")
    def _unique_slot_ids(self) -> ReportTemplate:
        ids = [slot.id for slot in self.slots]
        if len(ids) != len(set(ids)):
            raise ValueError("Slot ids must be unique within a template.")
        return self


class ReportTemplateRegistry:
    """Discover template definitions from the resources directory."""

    def __init__(self, directory: Path | None = None) -> None:
        self._directory = directory or resources_path("report_templates")
        self._templates = self._discover()

    def list_templates(self) -> list[ReportTemplate]:
        return [self._templates[name] for name in sorted(self._templates)]

    def get(self, name: str) -> ReportTemplate:
        template = self._templates.get(name)
        if template is None:
            raise ReportTemplateError(f"Unknown report template: {name}.")
        return template

    def _discover(self) -> dict[str, ReportTemplate]:
        if not self._directory.is_dir():
            return {}
        discovered: dict[str, ReportTemplate] = {}
        for path in sorted(self._directory.glob("*/metadata.json")):
            try:
                structure = json.loads(path.read_text(encoding="utf-8"))
                structure["theme"] = _load_theme(path.parent)
                template = ReportTemplate.model_validate(structure)
            except (OSError, ValueError, ValidationError) as error:
                raise ReportTemplateError(f"Report template at {path.parent.name} is invalid.") from error
            if template.name != path.parent.name:
                raise ReportTemplateError(
                    f"Report template in {path.parent.name} declares the name {template.name}."
                )
            discovered[template.name] = template
        return discovered


def _load_theme(directory: Path) -> dict[str, object]:
    """Read a directory's theme, falling back to the shared default."""

    path = directory / "theme.json"
    if not path.is_file():
        return DEFAULT_THEME.model_dump()
    return json.loads(path.read_text(encoding="utf-8"))
