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
