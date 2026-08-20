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

Prefer SQL for large-scale filtering, joins, grouping, and aggregation. Use
`analyze_dataset` only with a small dataset reference returned by `query_database` when it
adds value: descriptive statistics, correlation, distributions, transformations, cohorts,
outlier checks, or a matplotlib chart. For example, aggregate monthly revenue by channel in
SQL, then use Python for correlation or visualization; do not extract millions of raw events
for a Python groupby. The Python boundary has no credentials or database connection. Save
charts as PNG files in its working directory and let the runtime assign artifact filenames.
