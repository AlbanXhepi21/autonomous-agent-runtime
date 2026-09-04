# Generating reports outside a live run

This guide covers the **saved report** and **scheduled report** system — recurring or
reusable reports that recompute their own figures via the semantic metric pipeline,
without another agent turn. For a one-off report from a live analysis, see
[running-an-analysis.md](running-an-analysis.md).

## Creating a saved report

`POST /api/v1/workspaces/{workspace_id}/reports/saved` (`201`) with a
`SavedReportCreateRequest`:

```json
{
  "name": "Monthly Revenue Readout",
  "template_id": "monthly_business_review",
  "metric_requests": [
    {"metric": "revenue:v1", "dimensions": ["country"], "filters": [], "grain": "month"}
  ],
  "default_period": {"kind": "relative", "unit": "month", "offset": -1},
  "narrative_policy": "exclude"
}
```

`narrative_policy` controls what happens to prose across a rerun — `exclude` (no
narrative at all), `include_original` (requires `seed_narrative` and pins it to its
original period), or `require_new_investigation` (blocks automated execution entirely
until a fresh agent run seeds a narrative — see below). `metric_requests` (max 24) must
reference real, compiled metrics — see [semantic-metrics.md](../concepts/semantic-metrics.md)
for which of the 28 are actually rerunnable (`validated`/`production_ready`; `documented`
metrics cannot be used here, since there's no compiled SQL to rerun).

## Executing a saved report

`POST /workspaces/{workspace_id}/reports/saved/{id}/execute` with
`{"mode": "preview"|"publish", "formats": ["pdf"]}`. This is the non-agent pipeline:

1. `SavedReportExecutionService` resolves the saved report's `default_period`/
   `metric_requests` into concrete parameters.
2. Each metric is recompiled and re-executed via `MetricRunner` — through the identical
   `PostgreSQLQueryValidator` every other SQL path uses (see
   [data-analysis.md](../architecture/data-analysis.md#semantic-metric-execution)).
3. The result compiles into the same `CompiledReport` representation a live run's
   publish path uses, then renders PDF/DOCX identically.

If `narrative_policy == "require_new_investigation"`, execution is refused outright with
`409 {"code": "requires_new_investigation", ...}` — a saved report configured this way
can never auto-execute; it exists specifically to force a human (or a fresh agent run) to
produce a new narrative before anything is published again. A compilation/execution
failure returns `422 {"code": "execution_failed", ...}`.

## Reading execution history

`GET /workspaces/{workspace_id}/reports/saved/{id}/executions` — paginated
(`limit`/`offset`), returns one row per attempt (not latest-state-only — see
[persistence.md](../architecture/persistence.md#saved-reports)), each with `status`,
resolved period, `formats`, and `error_category` on failure.

`GET /workspaces/{workspace_id}/reports/saved/{id}/resolved-parameters` previews what a
run right now would resolve `default_period` to, without executing anything — useful for
confirming "last month" actually means what you expect before scheduling it.

## Scheduling recurring execution

`POST /workspaces/{workspace_id}/reports/scheduled` with a `saved_report_id`, a
`schedule` (`kind`, `hour`, `minute`, plus `day_of_week`/`day_of_month`/
`month_of_quarter` depending on `kind`), a `timezone`, and optionally a
`delivery_channel`/`delivery_destination` pair (link, webhook, or email — see
[reporting.md](../architecture/reporting.md)). Creation is rejected with `400
{"code": "requires_new_investigation", ...}` if the underlying saved report's
`narrative_policy` would block automated execution — this check happens at schedule-create
time, not just at execution time.

There is no delete endpoint — disable a schedule with `PATCH .../{id}` and `{"enabled":
false}` rather than removing it.

**Nothing runs a schedule automatically.** The scheduling worker
(`backend/scripts/run_scheduled_reports.py`) must be started explicitly — it claims due
schedules (`SELECT ... FOR UPDATE SKIP LOCKED`, safe across multiple worker processes),
executes each through the same non-agent pipeline described above, and retries on
failure. See [commands.md](../reference/commands.md) and
[operations/deployment.md](../operations/deployment.md) for running it in a real
deployment.

## Publishing from a saved report vs. a live run

Both paths converge on the same `CompiledReport` → PDF/DOCX rendering, but they are
different pipelines: a live run's publish path
(`POST .../analytics/runs/{run_id}/reports`) can include evidence/citations from the
agent's own trace; a saved report's execution path only ever reruns semantic metrics
against fresh data and, depending on `narrative_policy`, pins or excludes prose — it never
invokes the LLM. This is enforced structurally, not just by convention: a contract test
walks the full import graph of both the rerun/execution code and the live-run publishing
code and asserts neither can reach `app.llm` at all.
