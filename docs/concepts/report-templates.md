# Report templates

Five templates ship under
[`backend/app/resources/report_templates/`](../../backend/app/resources/report_templates),
each a `metadata.json` (structure) and a `theme.json` (style) pair — the separation is
enforced by a contract test, not just convention (see
[reporting.md](../architecture/reporting.md#template-metadata-and-themes)). All five
declare `report_type: "executive"` and support both PDF and DOCX output.

## `analysis_summary`

- **Purpose**: a single investigation written up as a shareable document, whatever period it covered.
- **Orientation**: portrait · **Period granularity**: custom
- **Sections (blocks, in order)**: cover → scope (required) → narrative "Executive Summary" (required) → metrics "Headline Metrics" → chart "Charts" (limit 6) → table "Supporting Tables" (limit 6) → caveats "Limitations" (required) → evidence "Evidence Appendix" (required)
- **Content slots**: `key_metrics` (kpi, 0–6, optional), `supporting_charts` (line/area/bar/stacked_bar/pie/scatter, 0–6, optional), `supporting_tables` (table, 0–6, optional)
- **Formats**: PDF, DOCX · **Theme**: `default` (see [Shared theme](#shared-theme-values) below)
- **Known limitation**: this is the only template where **no content slot is required** —
  every KPI, chart, and table is optional, so a sparse run can still produce a technically
  valid document with almost no populated content.

## `annual_review`

- **Purpose**: a full year of performance with trend charts and the queries behind every figure.
- **Orientation**: portrait · **Period granularity**: year
- **Sections**: cover → scope (required) → narrative "Executive Summary" (required) → metrics "Headline Metrics" (required, limit 8) → chart "Charts" (required, limit 6) → table "Supporting Tables" (required, limit 6) → caveats (required) → page break → evidence (required)
- **Content slots**: `headline_metrics` (kpi, 3–8, required), `primary_trend` (line/area, **1–2**, required), `key_breakdowns` (bar/stacked_bar/pie/scatter, 0–4, optional), `supporting_tables` (table, 1–6, required)
- **Formats**: PDF, DOCX · **Theme**: `default`
- **Known limitation**: `primary_trend` is capped at 2 trend charts even though it's
  required — a genuine ceiling on how much year-over-year trending this template can show.

## `executive_dashboard`

- **Purpose**: a one-page landscape summary — headline cards, the principal charts, and
  little else, with the full evidence kept behind it.
- **Orientation**: **landscape** (the only landscape template) · **Period granularity**: custom
- **Sections**: cover → metrics "Headline Metrics" (required, limit 6) → chart "Charts" (required, limit 4) → narrative "Executive Summary" (optional) → caveats (required) → page break → scope (required) → table "Supporting Tables" (optional, limit 8) → evidence (required) — note the unusual order: metrics/charts print *before* the narrative, and scope comes *after* the page break, reflecting the one-page-summary intent.
- **Content slots**: `headline_metrics` (kpi, 3–6, required), `primary_trend` (line/area, 0–1, optional), `primary_breakdown` (bar/stacked_bar, **exactly 1**, required), `secondary_breakdown` (bar/stacked_bar/pie/scatter, 0–2, optional), `supporting_table` (table, 0–2, optional)
- **Formats**: PDF, DOCX · **Theme**: `dashboard` (the only non-default theme — see below)
- **Known limitation**: `primary_breakdown` is both **required and hard-capped at exactly
  one** chart. Combined with the project's own documented tendency for the agent to
  produce only one display per run (see
  [charts-and-displays.md](charts-and-displays.md#current-limitations)), this slot is
  usually the one that gets filled — leaving `secondary_breakdown` and `primary_trend`
  often empty in practice, even though the template supports them.

## `monthly_business_review`

- **Purpose**: headline metrics, the month's movements, and the evidence behind them, for a recurring management readout.
- **Orientation**: portrait · **Period granularity**: month
- **Sections**: cover → scope (required) → narrative (required) → metrics (required, limit 8) → chart (required, limit 6) → table (required, limit 6) → caveats (required) → page break → evidence (required)
- **Content slots**: `headline_metrics` (kpi, 3–8, required), `primary_trend` (line/area, 0–2, optional), `key_breakdowns` (bar/stacked_bar/pie/scatter, **1–4, required**), `supporting_tables` (table, 1–6, required)
- **Formats**: PDF, DOCX · **Theme**: `default`

## `quarterly_review`

- **Purpose**: a quarter's performance with trend charts, supporting detail, and a full evidence appendix, for a stakeholder review pack.
- **Orientation**: portrait · **Period granularity**: quarter
- **Sections and slots**: structurally identical to `monthly_business_review` (same block order, same slot shapes) — only the title, description, and period granularity differ.
- **Formats**: PDF, DOCX · **Theme**: `default`

## Shared theme values

All five templates share the identical color palette and chart palette; only
`executive_dashboard` diverges in name, type sizes, spacing, and two style switches:

| Template | Theme name | Table style | Metrics style | Title/heading/body/caption sizes | Margin |
|---|---|---|---|---|---|
| analysis_summary | `default` | grid | table | 21/13/10/7.5 | 56 |
| annual_review | `default` | grid | table | 21/13/10/7.5 | 56 |
| monthly_business_review | `default` | grid | table | 21/13/10/7.5 | 56 |
| quarterly_review | `default` | grid | table | 21/13/10/7.5 | 56 |
| executive_dashboard | `dashboard` | rules | cards | 24/14/10.5/7.5 | 42 |

Shared palette (all 5): ink `#142033`, muted `#657188`, accent `#176b87`, rule `#e6eaf0`,
table header `#f2f8fa`. Shared chart palette: `#176b87, #3c9a79, #d1873b, #8064b5, #cc5b63`.
Fonts: Helvetica/Helvetica-Bold for PDF, Calibri for DOCX, across every template.

## Known limitations (cross-template)

- Every template is `report_type: "executive"` — there is no non-executive report
  category (e.g. a raw data-dump or a technical/engineering-audience template) shipped
  today.
- `executive_dashboard`'s required, exactly-one-chart `primary_breakdown` slot is the
  template most exposed to the agent's one-display-per-run tendency (see
  [charts-and-displays.md](charts-and-displays.md)) — it's also the template most likely
  to render close to its intended design from a single run, for the same reason.
- Templates are reviewed for layout regressions via
  `scripts/preview_reports.py` against fixed sample data, not against live runs — see
  [commands.md](../reference/commands.md).
