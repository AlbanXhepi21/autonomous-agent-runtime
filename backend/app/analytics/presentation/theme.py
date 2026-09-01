"""How a report looks, kept apart from what it contains.

Structure — which sections, in what order, with what limits — is a different
decision from typography and colour, and the two change for different reasons.
Splitting them means a new house style is a ``theme.json`` edit and a new
deliverable shape is a ``metadata.json`` edit, with neither able to alter the
other's meaning.

A theme can never add, remove or reorder a fact. It decides ink, not content.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: Hex colours only, so a theme cannot smuggle in an expression or a URL.
_HEX = r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$"


class ThemePalette(BaseModel):
    """The document's own colours."""

    model_config = ConfigDict(extra="forbid")

    ink: str = Field(default="#142033", pattern=_HEX)
    muted: str = Field(default="#657188", pattern=_HEX)
    accent: str = Field(default="#176b87", pattern=_HEX)
    rule: str = Field(default="#e6eaf0", pattern=_HEX)
    table_header: str = Field(default="#f2f8fa", pattern=_HEX)
    #: Used only where a reader must not skim past something, such as prose that
    #: no longer describes the figures beside it.
    warning: str = Field(default="#a4501f", pattern=_HEX)


class ThemeFonts(BaseModel):
    """Font families and the sizes the renderers scale from.

    Families are named for both back ends: reportlab needs a built-in PostScript
    name, python-docx needs an installed Windows/Office family. They are given
    separately rather than mapped, because guessing one from the other is how a
    document silently loses its typeface.
    """

    model_config = ConfigDict(extra="forbid")

    pdf_body: str = Field(default="Helvetica", max_length=64)
    pdf_bold: str = Field(default="Helvetica-Bold", max_length=64)
    docx_body: str = Field(default="Calibri", max_length=64)
    title_size: float = Field(default=21, gt=4, le=48)
    heading_size: float = Field(default=13, gt=4, le=36)
    body_size: float = Field(default=10, gt=4, le=24)
    caption_size: float = Field(default=7.5, gt=3, le=18)


class ThemeSpacing(BaseModel):
    """Page margins and the gaps between blocks, in points."""

    model_config = ConfigDict(extra="forbid")

    margin: float = Field(default=56, ge=18, le=144)
    block_gap: float = Field(default=10, ge=0, le=48)
    heading_gap: float = Field(default=7, ge=0, le=48)


class ReportTheme(BaseModel):
    """One visual style a report may be rendered in."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="default", min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    palette: ThemePalette = Field(default_factory=ThemePalette)
    fonts: ThemeFonts = Field(default_factory=ThemeFonts)
    spacing: ThemeSpacing = Field(default_factory=ThemeSpacing)
    #: Series colours, shared with the Matplotlib renderer so an exported chart
    #: keeps the palette the rest of the document is set in.
    chart_palette: list[str] = Field(
        default_factory=lambda: ["#176b87", "#3c9a79", "#d1873b", "#8064b5", "#cc5b63"],
        min_length=1, max_length=12,
    )
    #: Whether tables are drawn with full gridlines or horizontal rules only.
    table_style: Literal["grid", "rules"] = "grid"
    #: How headline metrics are set. ``cards`` is the boxed row a dashboard is
    #: read across; ``table`` is the column a report is read down. Presentation
    #: only — the same compiled metrics are printed either way.
    metrics_style: Literal["table", "cards"] = "table"


DEFAULT_THEME = ReportTheme()
