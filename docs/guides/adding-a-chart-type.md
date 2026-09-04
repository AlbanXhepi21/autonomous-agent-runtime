# Adding a chart type

Unlike tools, skills, specialists, and report templates, chart types are **not** a
discovered or plugin-based extension point. `ChartType`
(`backend/app/analytics/presentation/charts.py`) is a closed, 8-value `Literal`:
`line, bar, stacked_bar, area, pie, scatter, table, kpi`. Adding a 9th type means editing
code in several specific places, not dropping in a new file. This guide documents exactly
which places, verified against current code, not a hypothetical plugin API.

## 1. Relevant contract

`ChartSpec.type: ChartType` (`backend/app/analytics/presentation/charts.py`) — the field
whose Literal you're extending. `PLOTTED_TYPES` (a frozenset of everything except `table`
and `kpi`) gates whether `y_fields` is required and whether the "one row is not a chart"
rule applies — decide up front whether your new type belongs in that set.

## 2. Implementation location

Backend changes span three files at minimum:

1. **`backend/app/analytics/presentation/charts.py`** — add the value to the `ChartType`
   Literal, and to `PLOTTED_TYPES` if it's a plotted (not table/KPI) type.
2. **`backend/app/analytics/presentation/rasterize.py`** — add the value to the
   `RASTERIZABLE` frozenset and a drawing branch in `render_chart_png`/`_draw_series` (or
   `_pivot`, if it needs its own data-shaping). **If you skip this file, the chart type
   still validates and stores correctly, but silently cannot be rendered into a PDF or
   DOCX** — `documents.py`'s writer falls back to printing *"This chart could not be
   rendered for print."* instead of an image. This degrades gracefully, but only because
   the fallback exists — it is not the same as the type actually working end-to-end.
3. **`backend/app/analytics/presentation/templates.py`** — if the new type should be
   selectable in a report template's slot `accepts` list, it must fit one of the three
   existing slot "families" (`{"kpi"}`, `{"table"}`, or `PLOTTED_TYPES`) enforced by a
   model validator, or that validator needs to change too.

`compiler.py`, `document_model.py`, and `documents.py` need **no code change** — they
already degrade gracefully for an unrasterizable type (silently omitted from the printed
chart block; `documents.py` prints the fallback text above). Know this before assuming a
new type "isn't working" when actually only step 2 was skipped.

## 3. Registration / discovery

Not applicable — this is a closed enum, not a registry. The single source of truth is the
`ChartType` Literal in `charts.py`.

## 4. Security or capability requirements

None beyond what `create_chart` already requires (`Capability.ANALYTICS_REPORT_CREATE`,
auto-allowed in non-production). A new chart type doesn't change the tool's capability.

## 5. Tests required

- A `ChartSpec` validation test asserting the new type accepts valid data and rejects
  invalid data the same way existing plotted types do (see the validators in `charts.py`
  — non-scalar values, required fields present in `data`, minimum row count if plotted).
- A rasterization test asserting `render_chart_png` produces a real image for the new type
  (or, if you deliberately left it out of `RASTERIZABLE`, a test asserting the graceful
  fallback text appears instead — don't leave this unverified either way).
- If the type is added to a template slot's `accepts` list, `test_report_boundaries.py`'s
  slot-family validator will need the new type to fit an existing family or itself needs a
  matching update — run the report contract tests after any template change.

## 6. Documentation required

Update the chart type list and the field table in
[charts-and-displays.md](../concepts/charts-and-displays.md), and note in that page
whether the new type is rasterizable (appears in PDF/DOCX output) or browser-only.

## 7. Common mistakes

- Adding to `ChartType` but forgetting `RASTERIZABLE` — the type "works" in the Workbench
  (Recharts renders anything the frontend chart-renderer explicitly handles) but silently
  fails to print, which is easy to miss if you only test interactively in the browser.
- Forgetting the **frontend** side entirely: `frontend/src/features/workbench/components/chart-renderer.tsx`
  needs its own new rendering branch using Recharts primitives — the type flowing through
  the generated TypeScript types (`frontend/src/types/api.generated.ts`, regenerated via
  `npm run gen:api` after the backend change) does not automatically get a visual
  representation in the browser.
- Assuming there's a shared rendering code path between the browser (Recharts) and the
  server (Matplotlib) — there isn't. Both must be updated and will drift if only one is.
- Adding a type to a template slot's `accepts` list without checking
  `_SLOT_KIND_FAMILIES` in `templates.py` — a slot can only accept types from one family
  (kpi, table, or plotted); mixing families in one slot's `accepts` list fails validation.

## 8. Minimal example (illustrative, not a running diff)

Adding a hypothetical `histogram` type as a plotted, rasterizable type:

```python
# backend/app/analytics/presentation/charts.py
ChartType = Literal["line", "bar", "stacked_bar", "area", "pie", "scatter", "table", "kpi", "histogram"]
PLOTTED_TYPES = frozenset({"line", "bar", "stacked_bar", "area", "pie", "scatter", "histogram"})
```

```python
# backend/app/analytics/presentation/rasterize.py
RASTERIZABLE = frozenset({"line", "area", "bar", "stacked_bar", "pie", "scatter", "histogram"})

def render_chart_png(chart: ChartSpec, ...) -> Path | None:
    ...
    elif chart.type == "histogram":
        _draw_histogram(figure, chart)
    ...
```

```typescript
// frontend/src/features/workbench/components/chart-renderer.tsx
// after regenerating types with `npm run gen:api`:
if (chart.type === "histogram") {
  return <BarChart data={chart.data}>{/* Recharts has no native histogram primitive —
    bucketing must happen before the chart reaches this component */}</BarChart>;
}
```

This is illustrative only — a real histogram would need bucketing logic decided upstream
(likely in the SQL or in `analyze_dataset`, since `ChartSpec.data` is pre-baked rows with
no aggregation logic of its own), not shown here.
