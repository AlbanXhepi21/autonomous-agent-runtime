# Adding a report template

## 1. Relevant contract

Two files, two schemas, deliberately kept separate and enforced as separate by a contract
test (structure vs. style must never mix):

`ReportTemplate` (`backend/app/analytics/presentation/templates.py`, `extra="forbid"`) —
`metadata.json`:

```python
name: str                 # pattern ^[a-z0-9_]+$, must equal the directory name
version: str = "1"
title: str                 # 1-120 chars
description: str           # 1-400 chars
report_type: ReportType     # required
period_granularity: Literal["month","quarter","year","custom"]
orientation: Literal["portrait","landscape"] = "portrait"
formats: list[Literal["pdf","docx"]] = ["pdf","docx"]
blocks: list[TemplateBlock]   # 1-24 items
slots: list[TemplateSlot] = []  # 0-16 items
```

`TemplateBlock`: `kind: BlockKind` (one of `cover, scope, narrative, metrics, chart,
table, caveats, evidence, page_break`), `heading: str | None` (required unless `kind` is
`page_break`/`cover`), `required: bool = False`, `limit: int | None` (1-100).

`TemplateSlot`: `id` (pattern `^[a-z0-9_]+$`), `accepts: list[ChartType]` (1-8, must stay
within one family — `{"kpi"}`, `{"table"}`, or the plotted types), `minimum: int = 0`,
`maximum: int = 1` (must be ≥ minimum), `required: bool = False`, `role:
Literal["primary","supporting"] = "primary"`, `purpose_hint: str | None` (≤200 chars).

`ReportTheme` (`backend/app/analytics/presentation/theme.py`) — `theme.json`, every field
optional with a default: `name`, `palette` (6 hex colors), `fonts` (family names + 4 size
fields), `spacing` (margin/block_gap/heading_gap), `chart_palette` (list of hex colors),
`table_style: "grid"|"rules"`, `metrics_style: "table"|"cards"`.

## 2. Implementation location

`backend/app/resources/report_templates/<your_template_name>/`, containing
`metadata.json` and (optionally) `theme.json`.

## 3. Registration / discovery

Fully filesystem-based. `ReportTemplateRegistry`
(`backend/app/analytics/presentation/templates.py`) globs
`app/resources/report_templates/*/metadata.json` at construction, loads each directory's
`theme.json` if present (falling back to a built-in default theme if absent — an omitted
`theme.json`, or an empty `{}`, is valid), and enforces `name == directory_name`.

## 4. Security or capability requirements

None — templates only affect what a `generate_report`/`create_chart`-produced document
looks like, not what the agent is allowed to do.

## 5. Tests required

`backend/tests/contracts/test_report_boundaries.py` enforces two things automatically for
**every** shipped template, including a new one, the moment it exists on disk:

- `test_every_shipped_template_separates_structure_from_theme` — fails if your
  `metadata.json` text contains the substrings `"palette"`, `"fonts"`, `"spacing"`, or
  `"chart_palette"` (i.e., style leaking into structure), and fails if `theme.json` is
  missing from the directory entirely.
- `test_a_template_cannot_declare_an_unknown_block` — proves the block-kind vocabulary is
  closed; not something you need to re-test per template, but know that a typo'd `kind`
  value raises at load, not silently.

Beyond that, add your template to whatever exercises
`backend/tests/unit/analytics/test_report_publishing.py`/`test_report_limitations.py`'s
pattern — both construct `ReportTemplateRegistry()` against the real resources directory,
so a malformed new template fails those tests at setup. If your template introduces a new
slot shape worth its own coverage (an unusually tight `minimum`/`maximum`, for instance),
add a targeted unit test compiling a report against it with both under- and
over-populated slot content.

## 6. Documentation required

Add a full entry to [report-templates.md](../concepts/report-templates.md) — purpose,
orientation, block order, slots (with min/max/required), formats, and a one-line theme
summary — following the format of the existing five entries.

## 7. Common mistakes

- Putting style values (`palette`, `fonts`, `spacing`, `chart_palette`) inside
  `metadata.json` — the contract test rejects this by substring match, not just semantic
  validation, so even an unused/dead key with one of those names in `metadata.json` fails.
- A `slots` entry whose `accepts` list mixes families (e.g. `["kpi", "bar"]`) — this fails
  the slot-family validator; KPIs, tables, and plotted charts are three separate worlds.
- Setting `required: true` on a slot the agent is unlikely to fill given the project's
  documented "one display per run" tendency (see
  [charts-and-displays.md](../concepts/charts-and-displays.md)) — a required slot that
  rarely gets populated produces a report that often reads as incomplete. The shipped
  `executive_dashboard` template's `primary_breakdown` slot (required, capped at exactly
  one) is the closest existing precedent for how tightly to scope a required slot.
- Forgetting `heading` on a block whose `kind` isn't `page_break`/`cover` — required by a
  model validator.

## 8. Complete minimal example

`backend/app/resources/report_templates/quick_summary/metadata.json`:

```json
{
  "name": "quick_summary",
  "version": "1",
  "title": "Quick Summary",
  "description": "The shortest possible readout: headline numbers and nothing else.",
  "report_type": "executive",
  "period_granularity": "custom",
  "orientation": "portrait",
  "formats": ["pdf", "docx"],
  "blocks": [
    {"kind": "cover"},
    {"kind": "metrics", "heading": "Headline Metrics", "required": true, "limit": 4},
    {"kind": "caveats", "heading": "Limitations", "required": true},
    {"kind": "evidence", "heading": "Evidence Appendix", "required": true}
  ],
  "slots": [
    {
      "id": "headline_metrics",
      "accepts": ["kpi"],
      "minimum": 1,
      "maximum": 4,
      "required": true,
      "role": "primary",
      "purpose_hint": "headline"
    }
  ]
}
```

`backend/app/resources/report_templates/quick_summary/theme.json` — omit entirely to
inherit the built-in default theme, or supply just what differs:

```json
{}
```

No registration code is needed — the next `ReportTemplateRegistry()` construction
discovers `quick_summary` automatically. Preview it against fixed sample data before
relying on a live run:

```bash
cd backend && .venv/bin/python -m scripts.preview_reports
```
