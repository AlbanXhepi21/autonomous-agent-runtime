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
    #: Populated from the directory's ``theme.json``; not part of the structure
    #: file, so a restyle never edits the section list.
    theme: ReportTheme = Field(default_factory=lambda: DEFAULT_THEME)

    def supports(self, document_format: str) -> bool:
        return document_format in self.formats


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
