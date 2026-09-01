# Executive Reporting

Create concise, decision-oriented reports from evidence already gathered. Select report type
(executive, sales, marketing, customer, operations, or inventory) based on the request, and
include only sections supported by data. Prioritize business impact, state units and periods,
and distinguish percentages from percentage-point changes.

Every quantitative metric, finding, and recommendation must cite one or more `query_###`
references. Do not invent values to fill a standard layout. If a metric is unavailable or a
query failed, state the limitation plainly. Recommendations must name a specific action and
the observed evidence that motivates it. Use charts only when they clarify a trend or
comparison. Pass bounded dataset references to generate_report for CSV extracts.

Before assembling an executive or detailed report, use `update_investigation_plan` to state
the objective, request class (`executive_report` or `detailed_report`), the questions the
report must answer (for example: headline volume, rate against a valid denominator, breakdown
by the relevant dimensions, trend over the period, and supporting detail), and the outputs each
needs — typically a `kpi` for the headline figure, a `stacked_bar` or `bar` for a breakdown, a
`line` for a trend, and a `table` of supporting rows for a detailed report. Mark each item
answered, created, or blocked as the evidence and displays come in; the runtime will not accept
a claimed status it cannot verify, and will redirect `finish` back to you while a required item
is still pending and budget remains.
