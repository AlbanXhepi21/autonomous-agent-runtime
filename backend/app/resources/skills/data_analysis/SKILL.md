# Data Analysis

Use this skill to turn business questions into bounded, reproducible evidence. It is
guidance, not a required sequence: choose only the investigation steps the evidence needs.

Start by defining the metric, unit, population, period, comparison, and important exclusions.
Inspect schema before using unfamiliar tables or columns. Use SQL for relational joins,
filtering, aggregates, windows, and comparisons; keep raw result sets small. A query error is
evidence about the schema or assumption—revise it rather than guessing.

For sales, distinguish revenue, orders, units, AOV, and growth. For profitability, verify the
cost basis before calculating gross profit/margin and examine discounts or supplier costs where
relevant. For customers, separate new/repeat behavior, value, cohorts, and segments. Marketing
analysis should distinguish traffic, conversion, attributed revenue, and missing attribution.
Operations and inventory analyses should account for shipment completion, refunds, carriers,
warehouses, stock levels, movements, and availability.

For broad changes, decompose before attributing cause. Revenue can be orders × AOV; orders may
reflect traffic × conversion. Compare a meaningful baseline and select plausible dimensions
(channel, device, country, category, campaign, payment failures, stockouts, delivery) based on
initial evidence. Do not run every decomposition by default, repeat near-identical queries, or
mistake correlation for causation.

Use calendar periods deliberately for MoM, quarter, prior-period, or YoY analysis. Be explicit
about time boundaries and timezone assumptions. Never silently treat NULL as zero: determine
whether it means missing, unknown, anonymous, pending, failed, or not applicable.

## Investigating changes

Start with a material, period-aligned baseline. Use a decomposition as a hypothesis map, not a
mandatory DAG. For revenue: revenue = orders × AOV; orders can be investigated through sessions
and conversion; AOV through basket size, product mix, price/cost, and discounts. For refunds,
start with product/category and reason, then country, carrier, warehouse, and delivery timing if
the first split suggests them. For margin, separate volume/mix from price, unit cost, and
discount effects. Query the highest-impact split first and only pursue a branch when it can
materially explain the observed change.

Contribution analysis means comparing each dimension member's current-versus-baseline metric,
ranking absolute contribution to the total delta, and showing the denominator/remaining
unexplained delta. Use SQL for the grouped comparison. Use Python only for a bounded result when
sorting, a waterfall-style transformation, confidence intervals, or a chart improves clarity.

## Funnels, cohorts, and retention

Use a clearly stated funnel: sessions → product views → cart → checkout → purchase. Count a
session at most once per stage, define whether purchase is an order, a converted session, or a
completed payment, and calculate each stage conversion from the preceding stage. Segment by one
dimension at a time (device, channel, campaign, country, period); a falling conversion rate plus
stable traffic is evidence to investigate the affected stage, not proof of cause.

For cohorts, define cohort month as signup month or first delivered-purchase month before
calculating cohort age. Retention should state its denominator (for example, customers with any
later delivered order divided by cohort customers). Repeat purchase and cohort revenue are
different measures. Build cohort counts/revenue by month in SQL; a small matrix may be pivoted,
summarized, or plotted in Python.

## Statistical discipline

Choose simple, interpretable methods. Use medians and quantiles for skewed delivery times/order
values; IQR for distribution outliers; rolling means and percentage-change thresholds for trends;
and z-scores only where the baseline is reasonably stable. Report sample size and practical
impact. Correlation, confidence intervals, and two-group comparisons may support an association,
but never establish a causal claim. Label conclusions as observation, association, or likely
explanation. Stop once the answer is evidence-backed and further queries are unlikely to change
the decision; explain missing or insufficient data rather than searching indefinitely.

In the answer, lead with the conclusion, give the key numbers and comparison, distinguish
observation from interpretation, state material caveats, and cite `query_###` references for
database-backed statements. Avoid dumping SQL or generic business prose unless useful.

Write for a reader who cannot see your tools. Do not describe what you displayed ("this is
charted as a table"); state the finding and let the display stand beside it.

When a result breaks one dimension down by another — failures by method and reason, revenue
by category and month — create a `stacked_bar` so the composition is visible, and add a
`table` when the exact figures matter too. A headline figure the answer leads with belongs
in a `kpi` display so it appears as a headline metric rather than only in prose.

Repeat those material caveats in the finish action's `caveats` field — missing or
incomplete data, an ambiguous definition, a small sample, an unavailable dimension, a
period the data does not fully cover, possibly stale source data, or a result that should
not be generalized. They are printed verbatim as a published report's limitations, so keep
each to one short sentence and leave the list empty when there is nothing genuine to say.

Prefer SQL for large-scale filtering, joins, grouping, and aggregation. Use
`analyze_dataset` only with a small dataset reference returned by `query_database` when it
adds value: descriptive statistics, correlation, distributions, transformations, cohorts,
outlier checks, or a matplotlib chart. For example, aggregate monthly revenue by channel in
SQL, then use Python for correlation or visualization; do not extract millions of raw events
for a Python groupby. The Python boundary has no credentials or database connection. Save
charts as PNG files in its working directory and let the runtime assign artifact filenames.

`analyze_dataset` receives `analytics_data` as `{"columns": [...], "rows": [[...], ...]}`,
not a pandas DataFrame. Read the returned column names and map them to row indexes before
plotting. Do not assume names such as `month`; use the query's actual column labels. Avoid
`pathlib`, filesystem APIs, and database connections inside the restricted Python boundary.

## Interactive Workbench charts

Choose the display from the shape of the result. Three or more rows across a dimension, or
any series over time, belongs in a chart or table rather than in prose; a breakdown by two
dimensions belongs in a table. A long bulleted list of figures is a table that was not
created. A single figure, a yes/no answer, or a two-value comparison stays in the sentence,
and a number already stated plainly does not also need a chart.

When a display is warranted, prefer `create_chart` after `query_database`. It creates a validated, interactive data-only display in the Workbench; it
does not create React, JavaScript, HTML, or executable formatter code. Copy only a bounded set
of values from the query result, use the exact field names returned by SQL, and include the
actual `query_###` identifier in `source_query_ids`.

For a line chart, set `type` to `line`, give `x_field` the time column, give `y_fields` the
numeric metric column, and add the matching rows as scalar objects. A compact example is
`{"type":"line","title":"Monthly revenue","x_field":"month","y_fields":["revenue"],"data":[{"month":"2026-01","revenue":1200}],"source_query_ids":["query_001"]}`.

Use `line` or `area` for time trends, `bar` for category comparisons, `stacked_bar` for
composition, `pie` only for a small part-to-whole comparison, and `scatter` for relationships
between numeric variables. Use `table` for a compact result grid and `kpi` for a few headline
values. Do not use `analyze_dataset` merely to create a PNG when an interactive chart answers
the request. A PNG/chart artifact remains appropriate only when the user explicitly wants a
downloadable image or report artifact.

For a time comparison (for example, new versus returning customers), return one row per time
period with one numeric field per series, such as `month`, `new_orders`, and `returning_orders`.
Set both numeric fields in `y_fields` and give each a clear series label. Do not emit repeated
`month` rows with a separate `customer_type` field when a pivoted SQL aggregate can produce the
two series directly. Keep time axes bounded to the requested period so charts remain readable.

## KPI card requests

For a request such as “total revenue, gross margin, and month-over-month growth,” use a compact
workflow. Load this skill, then use `list_metrics` at most once only if the canonical metric
names are needed. Inspect `orders` and `order_items` only when their columns have not already
been observed. Run one bounded aggregate query that calculates the requested values together;
for a month-over-month value, calculate the current and immediately preceding comparable period
in the same query. After a successful query, call `create_chart` with `type: "kpi"`, 2–4
human-readable `kpis`, and the successful `query_###` in `source_query_ids`, then finish with a
short evidence-backed summary.

Do not repeatedly call `list_metrics`, `list_tables`, or `search_schema` after a useful result.
Do not load unrelated skills. If the first query fails, inspect the one relevant table, make one
corrected query, and finish with either the resulting KPI cards or a clear data limitation.
