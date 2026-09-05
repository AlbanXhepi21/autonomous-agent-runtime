# Reporting

This document covers how a completed agent run becomes a published PDF or Word document:
`backend/app/analytics/presentation/` (the compiler and both document writers),
`backend/app/orchestration/publishing.py` and `reruns.py`, `backend/app/reports/`, and
`backend/app/artifacts/`.

## The compiled report

Every report — whether from a live agent run or a saved-report execution — is turned into
one canonical intermediate representation, `CompiledReport`
(`backend/app/analytics/presentation/document_model.py`), by a single function,
`compile_report()`. Its own module docstring states the purpose plainly: a report is
compiled once, from a run that already happened, and the PDF writer and the DOCX writer
then walk the *same* blocks in the *same* order — neither renderer is given the run data
independently or allowed to choose its own facts.

## Block kinds

A `CompiledReport` is a list of typed blocks, one of nine kinds: `cover`, `scope`,
`narrative`, `metrics`, `chart`, `table`, `caveats`, `evidence`, `page_break`. A
`narrative` block's prose is further typed as heading, paragraph, bullet, or numbered
list. Every block kind is a discriminated Pydantic type, not a loosely-shaped dict — both
document writers dispatch on `block.kind` to decide how to render it.

## Template metadata and themes

Report templates (`backend/app/resources/report_templates/*/`) separate **structure**
from **style**, and that separation is enforced by a contract test
(`test_every_shipped_template_separates_structure_from_theme`), not just convention:

- `metadata.json` declares structure: template name, version, title, description, a
  `report_type` (executive/sales/marketing/customer/operations/inventory), period
  granularity, page orientation, supported output formats, the ordered list of blocks
  (kind, heading, whether required, any limit), and named "slots" that accept
  agent-produced content (with minimum/maximum counts and a role/purpose hint).
- `theme.json` declares style only: a hex-validated color palette, font choices and sizes,
  spacing, a chart color palette (shared with the Matplotlib renderer), and simple layout
  switches (table style, metrics-as-table-or-cards). Its own module docstring is explicit
  that "a theme can never add, remove, or reorder a fact."

Five templates ship today: `analysis_summary`, `annual_review`, `executive_dashboard`,
`monthly_business_review`, `quarterly_review` — all support both PDF and DOCX output.

## PDF generation

`_PdfWriter` (`backend/app/analytics/presentation/documents.py`) uses reportlab's
`SimpleDocTemplate` with page size and orientation chosen from the template. Each block
kind is rendered by a same-named method, dispatched dynamically from `block.kind`.
Headings and body text become `Paragraph` flowables; tables and metric "cards" become
reportlab `Table`/`TableStyle`; charts become sized `Image` flowables built from the
pre-rasterized PNGs (see below); bullets/numbered lists become `ListFlowable`; running
header, footer, and page numbers are drawn directly on the canvas so they appear on every
page consistently.

## DOCX generation

`_DocxWriter` (same file) uses python-docx: `add_heading`/`add_paragraph` for text,
`add_picture` for chart images, `add_table` (styled `"Light Grid Accent 1"`) for tables and
metric cards, with landscape page setup swapped in for wide reports. Page numbers are
inserted as a real Word field (raw OOXML `w:fldChar`), so Word computes them — they are not
hardcoded text — and table headers are flagged to repeat across page breaks via OOXML.
Both writers share an identical method signature, checked by a contract test, so neither
can silently diverge in what inputs it expects.

## Matplotlib chart rendering

Charts are rasterized once, before either writer runs, by
`backend/app/analytics/presentation/rasterize.py`: it draws directly onto a
`matplotlib.figure.Figure` bound to `FigureCanvasAgg`, explicitly bypassing `pyplot`
because pyplot's global figure state is not safe to share across concurrent requests. The
same `ChartSpec` type the frontend renders with Recharts is the input here — the module's
own comment notes its layout logic deliberately mirrors the frontend's chart-preparation
function by hand, since there is no shared code path between a browser (Recharts) and this
server-side path. Output is a fixed 8×4 inch PNG at 144 DPI. Table and KPI-card block kinds
are not rasterized as images — they're rendered as native document text/tables in each
writer instead. The same rasterized images are handed to both the PDF and DOCX writer, so
the two formats cannot end up showing different pictures for the same chart.

## Evidence appendix

A distinct `evidence` block renders one entry per cited query: its ID, description, when
it ran, the period/parameters/dimensions it used, which tables and columns it touched, row
count, whether it was truncated, and — for reruns — which figures it fed. Sources come from
`query_ledger`/`resolve_citations`
(`backend/app/observability/evidence.py`), which are built from the run's own trace events
for a live agent run, or from the rerun service for a recomputed report. A fixed notice is
always attached alongside evidence, clarifying that a citation proves the query executed —
not that its arithmetic is correct.

## Narrative freshness

When a report's figures are recomputed against a different period or filters than its
narrative prose was originally written for, the report carries an explicit
`NarrativeStatus`: `current`, `pinned_to_original_period`, or
`excluded_from_refreshed_report`. Depending on the case, the compiler either prints a loud
warning sentence alongside the (now possibly mismatched) prose, or drops the prose
entirely with an explanatory message — republishing itself never fails outright; a
contract test enforces that neither format is allowed to reuse stale prose silently
without one of these two visible signals.

## Parameterized reruns

`ReportRerunService` (`backend/app/orchestration/reruns.py`) recomputes a report's figures
by re-running its underlying semantic metric definitions through the same
compile-then-validate-then-execute path described in
[data-analysis.md](data-analysis.md#semantic-metric-execution) — it does **not** replay
the agent's original SQL, deliberately: SQL the agent wrote for one question was never
reviewed as a reusable statement. Varying the metric, period, dimensions, filters, or
grain produces new figures without another agent turn. This is structurally enforced, not
just documented: contract tests walk the actual import graph of both the rerun/execution
code and the publishing code and assert neither can reach `app.llm` at all.

## Report-defaults precedence

`ReportPreferences` (`backend/app/tenancy/contracts.py`, one row per workspace) holds a
workspace's own presentation defaults — `default_template`, `default_output_format`,
`default_theme`, `default_narrative_policy`, and the two appendix flags. Resolving what a
publish actually uses follows one precedence, applied in
`app.api.routes.analytics._resolve_template`/`_resolve_formats`:

```text
explicit request parameter → workspace's own ReportPreferences → system default
```

`template` has no system default — a request that omits it and whose workspace has no
`default_template` either is refused with `422 {"code": "template_required", ...}` rather
than guessing. `formats` falls back to `["pdf"]` when neither is set. `default_template` is
validated against the live `ReportTemplateRegistry` when it's set (an unknown template id is
rejected at `PATCH .../report-preferences` time, not discovered later at publish time).
`default_theme` and `technical_sql_appendix_enabled` are stored but not yet consulted by any
renderer — see [Known limitations](#known-limitations).

This resolution never reads the requesting *user's* personal preferences (`preferred_timezone`
etc. on `User`) — only the request itself and the target workspace's own settings, so who
happens to click "publish" cannot change what an organization's report contains. The
workspace's `default_locale`/`default_timezone`/`default_currency` (`Workspace`, not
`ReportPreferences`) are resolved the same way — workspace setting only, no request-level
override exists yet — and stamped into the published artifact's `metadata` as
`resolved_locale`/`resolved_timezone`/`resolved_currency`, so the document stays
reproducible even after the workspace's settings change later. A `ReportPreferences` or
`Workspace` update never rewrites a `metadata` value already stamped onto a previously
published artifact.

## Artifact lifecycle

Every artifact (a chart image, a published PDF/DOCX, a CSV extract) has exactly one of
four statuses: `PENDING` (registered, bytes not yet confirmed written), `READY` (bytes
verified on disk), `FAILED` (write failed), `DELETED` (retention expired and bytes
removed, row kept as an audit trail). A row never moves back out of `DELETED` or `FAILED`
into `READY`. Retention is one of `standard` (subject to expiry), `legal_hold`, or
`permanent` — the retention worker's own database query excludes the latter two from
consideration, so they can't be swept even if invoked directly. Expired-artifact claiming
uses row-level locking so multiple worker processes can run safely against the same
database, with a bounded retry count before giving up on a deletion rather than retrying
forever.

## PDF-authoritative policy

The codebase states this policy explicitly and shows it to the reader, not only in a code
comment: a fixed notice ("the published PDF is the authoritative record of this report's
figures and layout; a Word copy is provided for editing and reuse; once edited it is no
longer a record of what this run produced") appears on report previews, and a twin notice
is printed visibly on the DOCX's own cover page. Beyond the visible disclaimer, the policy
is architecturally reinforced: both formats are rendered from the same `CompiledReport`
object and the same pre-rasterized chart images, and both writers are contract-tested to
share an identical signature — so neither renderer can independently decide what a figure
says. There is, however, no automated test that diffs every rendered figure between the
PDF and DOCX outputs for arbitrary content; format equivalence rests on the shared-input
architecture rather than an exhaustive output comparison (narrative-freshness text is the
one case that is explicitly diffed across both formats).

## Known limitations

- PDF/DOCX figure equivalence is architecturally guaranteed by a shared compilation step,
  not independently verified by a full output-diffing test.
- Semantic metrics — and therefore parameterized reruns — are not available against
  workspace-connected data sources today; both operate against the fixed demo schema.
- `ReportPreferences.default_theme` and `technical_sql_appendix_enabled` are stored and
  validated but not yet consulted by any renderer: no request parameter selects a theme
  today (a template's `theme` is fixed on the template itself), and no current template
  prints a SQL appendix. `default_template`/`default_output_format` are the two preferences
  actually applied — see [Report-defaults precedence](#report-defaults-precedence).
