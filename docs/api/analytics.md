# API: Analytics

The Workbench's actual workflow — `/api/v1/workspaces/{workspace_id}/analytics/*`. All
routes require the standard tenant context and, for mutating calls, `X-CSRF-Token` (see
[overview.md](overview.md)). Compare with `POST
/api/v1/workspaces/{workspace_id}/agent/run` (a simpler, plain goal-driven endpoint the
Workbench UI does **not** use — see
[frontend.md](../architecture/frontend.md#the-workbench-feature-module)).

## Start a run

```http
POST /runs
{"message": "What is total revenue?", "conversation_id": null}
```

`202 Accepted` →

```json
{"run_id": "...", "conversation_id": "...", "status": "running"}
```

Omit `conversation_id` to start a new conversation; pass an existing one to continue it.

## Read a run

```http
GET /runs/{run_id}
```

`200` → `RunResponse`:

```json
{
  "run_id": "...", "conversation_id": "...",
  "status": "running" | "completed" | "failed" | "waiting_for_approval",
  "created_at": "...", "started_at": "...", "finished_at": "...",
  "final_response": "...", "error": null,
  "metrics": {"...": "..."} ,
  "charts": [/* ChartSpec, see charts-and-displays.md */],
  "sources": [/* AnswerSource, see evidence-and-citations.md */],
  "caveats": ["..."]
}
```

`404 {"code": "unknown_run", ...}` if the run doesn't exist in this workspace.

## Stream progress

```http
GET /runs/{run_id}/events
Accept: text/event-stream
```

See [streaming-events.md](streaming-events.md) for the full event contract.

```http
GET /runs/{run_id}/events/history
```

`200` → `{"items": [/* every PublicRunEvent so far */]}` — a full, unpaginated replay used
to hydrate a run restored from conversation history, not for live gap-filling.

## Report suitability and preview

```http
GET /runs/{run_id}/report-suitability
```

Returns which registered templates the run's actual output can currently populate.

```http
POST /runs/{run_id}/report-preview
{"template": "monthly_business_review", "period": null, "title": null, "metrics": [], "narrative": null}
```

`template` is optional: omit it and the workspace's own `report-preferences.default_template`
(`/api/v1/workspaces/{workspace_id}/report-preferences`, see
[reports-and-artifacts.md](reports-and-artifacts.md)) is used instead; if the workspace has
no default either, this returns `422 {"code": "template_required", ...}`. An explicit
`template` always wins over the workspace default — see
[reporting.md](../architecture/reporting.md) for the full precedence chain.

Produces a `ReportPreview` **without registering any artifact** — nothing is published or
persisted by this call. `metrics` (max 8) lets you preview with different
`MetricParameters` than the run originally used.

## Templates and metrics

```http
GET /report-templates
```

`200` → `{"items": [{"name", "title", "description", "report_type", "period_granularity", "sections": [...]}]}`
— a full, unpaginated list. See [report-templates.md](../concepts/report-templates.md).

```http
GET /metrics
```

`200` → `{"items": [{"name", "display_name", "description", "unit", "format", "dimensions", "filters", "grains", "value_columns", "required_tables", "caveats", "lifecycle_status"}]}`
— a full, unpaginated list across all 28 metrics. See
[semantic-metrics.md](../concepts/semantic-metrics.md).

## Publish a report

```http
POST /runs/{run_id}/reports
{"template": "monthly_business_review", "formats": ["pdf"], "period": null, "title": null, "metrics": [], "narrative": null}
```

`template` and `formats` are both optional, resolved the same way as
`report-preview` above: an explicit value in the request wins; otherwise the workspace's
`report-preferences.default_template`/`default_output_format` applies; `formats` finally
falls back to `["pdf"]` if the workspace has no default either (`template` has no such
system default — it 422s instead, see above). The response's `template` field always names
the template actually used, even when the caller didn't send one. The published artifact's
metadata additionally records `resolved_locale`, `resolved_timezone`, and
`resolved_currency` — the workspace's own regional settings at publish time, stamped in for
reproducibility (see [reporting.md](../architecture/reporting.md)); these never come from
the requesting user's personal preferences, and changing the workspace's settings afterward
never rewrites an already-published document.

`201` →

```json
{
  "run_id": "...", "template": "monthly_business_review",
  "documents": [{"artifact_id": "...", "name": "...", "media_type": "application/pdf", "size": 123456}],
  "narrative": "...",
  "rerun_query_ids": ["rerun_001"]
}
```

`rerun_query_ids` is populated whenever a figure was recomputed via the metric pipeline
rather than taken directly from the run's own evidence — see
[evidence-and-citations.md](../concepts/evidence-and-citations.md#creation-of-rerun-evidence).
Download the resulting documents via `GET /artifacts/{artifact_id}` — see
[reports-and-artifacts.md](reports-and-artifacts.md).
