# API: Reports and artifacts

Covers saved reports, scheduled reports, and artifact download — see
[generating-reports.md](../guides/generating-reports.md) for the workflow these support
and [reporting.md](../architecture/reporting.md) for the underlying pipeline.

## Saved reports — `/api/v1/workspaces/{workspace_id}/reports/saved`

```http
POST ""
{
  "name": "Monthly Revenue Readout",
  "template_id": "monthly_business_review",
  "metric_requests": [{"metric": "revenue:v1", "dimensions": ["country"], "filters": [], "grain": "month"}],
  "default_period": {"kind": "relative", "unit": "month", "offset": -1},
  "narrative_policy": "exclude"
}
```

`201` → `SavedReportResponse` (`id, workspace_id, owner, name, description, template_id,
template_version, narrative_policy, status, version, created_at, updated_at,
metric_requests, default_period, seed_run_id, seed_narrative, seed_narrative_period`).

```http
GET ""                       # paginated: limit, offset -> {items, total, limit, offset}
GET /{id}
PATCH /{id}
POST /{id}/archive
```

`PATCH`/other mutating calls on a saved report use optimistic concurrency — a version
mismatch returns `409 {"code": "version_conflict", "expected_version": N, "actual_version": M}`.

```http
GET /{id}/resolved-parameters
```

Previews what `default_period` currently resolves to, without executing anything.

```http
POST /{id}/execute
{"mode": "preview" | "publish", "formats": ["pdf"]}
```

`200` → `{"execution_id", "run_id", "mode", "status", "resolved_period_start",
"resolved_period_end", "preview": null_or_ReportPreview, "documents": [...]}`. `409
{"code": "requires_new_investigation", ...}` if the saved report's `narrative_policy`
blocks automated execution. `422 {"code": "execution_failed", ...}` on a metric
compilation/execution failure.

```http
GET /{id}/executions           # paginated -> {items, total, limit, offset}
```

One row per attempt (a genuine history, not latest-state), each with `id, run_id, mode,
status, resolved_period_start, resolved_period_end, formats, error, created_at,
completed_at, artifacts`.

## Scheduled reports — `/api/v1/workspaces/{workspace_id}/reports/scheduled`

```http
POST ""
{
  "saved_report_id": "...",
  "schedule": {"kind": "monthly", "hour": 6, "minute": 0, "day_of_month": 1},
  "timezone": "America/New_York",
  "formats": ["pdf"],
  "delivery_channel": "email",
  "delivery_destination": "team@example.com"
}
```

`201` on success; `400 {"code": "requires_new_investigation", ...}` if the underlying
saved report's `narrative_policy` would block automated execution — checked at
schedule-creation time, not only at execution time.

```http
GET ""                # paginated -> {items, total, limit, offset}
GET /{id}
PATCH /{id}            # e.g. {"enabled": false} to disable
```

**There is no delete endpoint** — disable a schedule with `PATCH` rather than removing it.
Response shape: `id, saved_report_id, workspace_id, schedule, timezone, formats,
delivery_channel, delivery_destination, enabled, next_run_at, last_run_at, last_result,
consecutive_failures, created_at, updated_at`.

Nothing executes a due schedule automatically — see
[generating-reports.md](../guides/generating-reports.md#scheduling-recurring-execution)
and [operations/deployment.md](../operations/deployment.md).

## Artifacts — `/artifacts` (no `/api/v1`, no workspace path segment)

```http
GET /artifacts/{artifact_id}
```

Downloads the file (`FileResponse`) — but **only if the artifact's status is `READY`**.
Anything `PENDING`, `FAILED`, or `DELETED` returns a plain `404 {"detail": "Artifact not
found."}` — indistinguishable from an ID that never existed. There is no distinct status
code for "exists but not ready yet."

```http
GET /artifacts?workspace_id={id}&run_id={optional}
```

`200` → a **bare, unpaginated array** of `ArtifactMetadata` (`artifact_id, run_id, name,
type, size, created_at, media_type, metadata`) — note `status` is **not included** in this
response at all, because the underlying store only ever lists `READY` artifacts; a
pending or failed artifact simply never appears in the list.

```http
GET /artifacts/{artifact_id}/preview
```

Renders inline for `image/png`/`image/jpeg` (`FileResponse`); returns a truncated
(≤65,536 characters) JSON body for `text/markdown`, `text/csv`, `application/json`,
`text/plain`; `415 {"detail": "Artifact preview is not supported."}` for anything else.

Authorization here is deliberately **not** the standard `require_permission`/
`get_tenant_context` dependency — because the URL has no `workspace_id` segment (so a
delivered link stays stable forever), each route performs its own membership check by
hand. See [artifacts.md](../concepts/artifacts.md#serving) and
[security-boundaries.md](../architecture/security-boundaries.md).
