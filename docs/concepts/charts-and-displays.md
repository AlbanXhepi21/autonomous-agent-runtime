# Charts and displays

## Supported chart types

`ChartType` (`backend/app/analytics/presentation/charts.py`) — exactly 8 values:
`line`, `bar`, `stacked_bar`, `area`, `pie`, `scatter`, `table`, `kpi`.

## The `ChartSpec` contract

Every chart or display the agent produces is a `ChartSpec` — a validated, bounded Pydantic
model (`extra="forbid"`), never a live component or a code fragment:

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Defaults to a generated UUID string, ≤80 chars |
| `type` | `ChartType` | Required |
| `title` | `str` | Required, 1–160 chars |
| `description` | `str \| None` | ≤500 chars |
| `x_field` | `str \| None` | ≤80 chars |
| `y_fields` | `list[str]` | ≤8 entries |
| `series` | `list[ChartSeries]` | ≤8 entries; each has `field` (required) and an optional `label` |
| `data` | `list[dict[str, Any]]` | ≤100 rows |
| `source_query_ids` | `list[str]` | **≥1, ≤12 entries** — see [Dataset references](#dataset-references) |
| `kpis` | `list[KPIItem]` | ≤8 entries |
| `formatting` | `ChartFormatting` | `currency`, `decimal_places` (0–4), `show_legend` |

Cross-field validation enforced by the model itself, not by a caller's discipline:

- A `kpi` chart requires at least one `KPIItem`; every other type requires non-empty `data`.
- A plotted type (everything except `table`/`kpi`) with fewer than 2 data rows is
  rejected — *"A chart of one value is not a chart. State the value in the answer, or use
  a kpi display for a headline metric."*
- Every field named in `x_field`, `y_fields`, or a series must actually appear as a key in
  the supplied `data` rows, or the chart is rejected.
- A non-table, non-pie, non-kpi chart with no `y_fields` is rejected.
- Every data value must be a scalar (`str`/`int`/`float`/`bool`/`None`) — this is the
  structural mechanism behind the data-only guarantee below, not a separate check.

### Example: a contract-valid bar chart

```json
{
  "type": "bar",
  "title": "Revenue by Region — Q2 2026",
  "x_field": "region",
  "y_fields": ["revenue"],
  "data": [
    {"region": "North America", "revenue": 152000},
    {"region": "Europe", "revenue": 98000},
    {"region": "Asia Pacific", "revenue": 76500}
  ],
  "source_query_ids": ["query_001"],
  "formatting": {"currency": "USD", "decimal_places": 0}
}
```

## The data-only constraint

Stated directly in the module docstring: *"Validated, data-only analytical displays.
Never contains executable frontend code."* `ChartFormatting` is separately documented as
*"a small, non-executable formatting vocabulary for the shared renderer."* The enforcement
mechanism is the scalar-only validator on `data` — there is no field type on `ChartSpec`
that could hold a function, a template string with interpolation, or arbitrary markup;
every value that reaches a renderer has already been checked to be a plain string, number,
boolean, or null.

## Dataset references

A `ChartSpec` links back to the query results it was built from exclusively through
`source_query_ids` — the `query_###` identifiers a `query_database` call produced earlier
in the same run (see [evidence-and-citations.md](evidence-and-citations.md)). There is no
separate `dataset_id` field on the chart itself. A `KPIItem` additionally pins its
`raw_value` to a specific `source_column` and `row_selector` within one
`source_query_id`, so a single headline number can be traced back to a specific cell, not
just a query.

## Filters and sorting

**`ChartSpec` has no filter field and no sort field.** Its complete field set is the 12
fields listed above — none express a filter predicate or an ordering. Any filtering or
sorting the agent wants reflected in a chart must already have happened upstream, in the
SQL that produced `data` — the chart itself is a fixed, pre-baked snapshot of rows.

## Frontend rendering

The Workbench renders a `ChartSpec` in the browser with **Recharts**
(`frontend/src/features/workbench/components/chart-renderer.tsx`), against the exact same
`ChartSpec`/`ChartType` shape generated from the backend's OpenAPI schema — see
[frontend.md](../architecture/frontend.md#api-client-and-the-openapi-codegen-pipeline).

## Server-side document rendering

For a published PDF or DOCX, the identical `ChartSpec` is rasterized a second time,
independently, by `backend/app/analytics/presentation/rasterize.py`, using Matplotlib
bound directly to `FigureCanvasAgg` (bypassing `pyplot`'s shared global state). Its own
comment notes the layout logic deliberately mirrors the frontend's chart-preparation code
by hand, since there is no shared rendering path between a browser and this server-side
step — see [reporting.md](../architecture/reporting.md#matplotlib-chart-rendering). Table
and KPI block kinds are never rasterized as images; both writers render them as native
document tables/text instead.

## Display budgets and investigation planning

`InvestigationPlan` (`backend/app/contracts/investigation.py`) defines suggested
`DISPLAY_BUDGETS` — a `(minimum, maximum)` tuple per request class:

| Request class | Suggested displays |
|---|---|
| `simple_fact` | 0–1 |
| `comparison` | 1–2 |
| `investigation` | 2–4 |
| `executive_report` | 3–6 |
| `detailed_report` | 5–8 |

The module is explicit that these are budgets, not mandatory counts — nothing enforces
that a run reach the lower bound. A plan's own `maximum_displays` field is capped at 8,
matching the one **hard** limit that actually exists: `ChartSpecStore.add` raises if a run
tries to register a ninth chart (*"A run may create at most eight analytical
displays."*). That ceiling, not the plan's budget, is what a run can never exceed.

## Current limitations

- **No filter or sort field on `ChartSpec`** — any such logic must be baked into the
  underlying SQL before the chart is created.
- **The agent tends to produce one display per run in practice**, per the project's own
  README — this is an observed behavioral tendency, not a coded limit (the coded limit is
  8 per run, far higher). A question asking for several charts often yields fewer, and a
  report section may print "This analysis produced no charts." The Executive Dashboard
  template is best previewed fully populated via `scripts/preview_reports.py` rather than
  a live run — see [commands.md](../reference/commands.md).
- **Two independent renderers must be kept in sync by hand** (Recharts in the browser,
  Matplotlib on the server) — there is no shared rendering code path between them, only a
  shared data contract.
