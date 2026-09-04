# Running an analysis

This walks the full path from asking a question to holding a published document, at both
the user (Workbench UI) and developer (raw API) level. For the underlying mechanisms, see
[agent-runtime.md](../architecture/agent-runtime.md),
[evidence-and-citations.md](../concepts/evidence-and-citations.md), and
[reporting.md](../architecture/reporting.md).

## Starting an analysis

**User flow**: type a question into the Workbench chat composer and submit.

**Developer flow**: this calls
`POST /api/v1/workspaces/{workspace_id}/analytics/runs` (see
[api/analytics.md](../api/analytics.md)) with a `CreateRunRequest` — `{"message": "...",
"conversation_id": null}` to start a new conversation, or an existing `conversation_id` to
continue one. The response (`202 Accepted`) is a `CreateRunResponse`:
`{"run_id": "...", "conversation_id": "...", "status": "running"}`. If the workspace has an
active connected data source, the run's analytics tools are scoped to it; otherwise the
built-in demo database is used.

## Watching SSE progress

**User flow**: the Workbench's investigation-progress view updates live as the run
proceeds — tool calls, chart creation, plan updates.

**Developer flow**: open `GET /api/v1/workspaces/{workspace_id}/analytics/runs/{run_id}/events`
as a `text/event-stream`. Each named SSE event carries a JSON `PublicRunEvent` in its
`data:` field — see [api/streaming-events.md](../api/streaming-events.md) for the full
list of 24 event types. The stream closes automatically once the run reaches a terminal
state. A browser's native `EventSource` handles reconnection with `Last-Event-ID`
automatically; reconnection only resumes within the same server process, since run state
is in-memory (see [persistence.md](../architecture/persistence.md#messages-and-traces)).

## Reading evidence

**User flow**: citations in the answer (`query_001`, `query_002`, ...) are attached as
`answer_sources` in the completed run — the Workbench surfaces these as the evidence
backing each figure.

**Developer flow**: `GET /api/v1/workspaces/{workspace_id}/analytics/runs/{run_id}`
returns a `RunResponse` including `sources: list[AnswerSource]` and `caveats: list[str]`.
Remember what a citation actually proves — see
[evidence-and-citations.md](../concepts/evidence-and-citations.md) for the precise
guarantee (execution, not narrative correctness).

## Viewing displays

Charts and KPIs the run produced are returned as `charts: list[ChartSpec]` in the same
`RunResponse`. The Workbench renders these with Recharts — see
[charts-and-displays.md](../concepts/charts-and-displays.md) for the contract and its
current one-display-per-run tendency.

## Selecting a report template

`GET /api/v1/workspaces/{workspace_id}/analytics/report-templates` lists every registered
template (`name, title, description, report_type, period_granularity, sections`). Pick one
whose `report_type`/`period_granularity` fits the analysis — see
[report-templates.md](../concepts/report-templates.md) for the full catalog of all five.

## Previewing

**Implemented.** `GET /api/v1/workspaces/{workspace_id}/analytics/runs/{run_id}/report-suitability`
returns which templates the run's actual output can populate; `POST
.../runs/{run_id}/report-preview` (body: `template`, optional `period`/`title`/`metrics`/
`narrative`) returns a `ReportPreview` without registering any artifact — nothing is
published or persisted by a preview call.

## Publishing PDF/DOCX

`POST /api/v1/workspaces/{workspace_id}/analytics/runs/{run_id}/reports` (`status_code:
201`) with a `PublishReportRequest` (`template`, `formats: ["pdf"]` or `["pdf","docx"]`,
optional `period`/`title`/`metrics`/`narrative`) compiles the run into a `CompiledReport`
and renders every requested format from that single compiled representation — see
[reporting.md](../architecture/reporting.md#pdf-authoritative-policy) for why PDF and DOCX
can never show different figures for the same run. The response,
`PublishReportResponse`, includes `documents: [{artifact_id, name, media_type, size}, ...]`
and `rerun_query_ids` if any figures were recomputed rather than taken directly from the
run.

## Downloading artifacts

`GET /artifacts/{artifact_id}` — note this route has **no `/api/v1` prefix and no
`workspace_id` path segment**, deliberately, so a link already sent in an email or webhook
never breaks (see [artifacts.md](../concepts/artifacts.md#serving)). It performs its own
membership check rather than the usual per-route dependency. Only `READY` artifacts are
ever returned; anything `PENDING`/`FAILED`/`DELETED` yields a plain 404, indistinguishable
from a nonexistent ID. `GET /artifacts/{artifact_id}/preview` renders images inline and
truncates text-based previews; unsupported media types return 415.

## Parameterized reruns

Applies to **saved reports**, not a live run directly — see
[generating-reports.md](generating-reports.md) for creating one. Once a saved report
exists, `POST /workspaces/{workspace_id}/reports/saved/{id}/execute` recomputes its
figures via the semantic metric pipeline (never another agent turn) with whatever
parameters the saved report's `metric_requests` specify.

## Narrative freshness

If a report's prose narrative was written for a different period or filters than the
figures it's now being shown alongside (most commonly after a rerun), the report carries
an explicit `narrative_status` — `current`, `pinned_to_original_period`, or
`excluded_from_refreshed_report` — and either prints a visible warning or omits the prose
with an explanation. It never silently shows mismatched prose as if it were still
accurate. Full mechanism in
[reporting.md](../architecture/reporting.md#narrative-freshness).
