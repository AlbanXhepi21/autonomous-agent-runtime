# Data Analyst Workbench API (UI1)

UI1 adds a frontend-facing adapter only. It does not change the AgentRunner, memory
model, or internal trace contract. Runs and conversations are process-local for now;
memory remains curated agent context and traces remain operational history.

## Routes

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/analytics/runs` | Start an asynchronous Data Analyst run (`202`). |
| `GET` | `/api/v1/analytics/runs/{run_id}` | Read a safe run summary. |
| `GET` | `/api/v1/analytics/runs/{run_id}/events` | Consume ordered server-sent progress events. |

```bash
curl -X POST http://localhost:8000/api/v1/analytics/runs \
  -H 'content-type: application/json' \
  -d '{"message":"Why did revenue fall in April 2026?"}'

curl -N http://localhost:8000/api/v1/analytics/runs/RUN_ID/events
curl http://localhost:8000/api/v1/analytics/runs/RUN_ID
```

SSE event payloads use `id`, `run_id`, `type`, `timestamp`, and `data`. Event IDs are
the existing immutable trace IDs. Reconnect with `Last-Event-ID`; the endpoint replays
subsequent stored trace events in recorder order. Open runs emit a keepalive comment.

Public types are: `run.started`, `run.completed`, `run.failed`, `agent.started`,
`agent.completed`, `skill.loaded`,
`schema.tables_listed`, `schema.table_described`, `sql.query_started`,
`sql.query_completed`, `sql.query_failed`, `sql.query_rejected`,
`python.analysis_started`, `python.analysis_completed`, `artifact.created`,
`chart.created`, `report.created`, `delegation.started`, and `delegation.completed`.

SQL events expose only query ID, duration, row count, referenced tables, truncation, and
safe failure category. UI1 never emits SQL text, prompts, action reasoning, observation
contents, credentials, or arbitrary trace metadata. `ANALYTICS_UI_EXPOSE_SQL` is retained
as an explicit deployment setting but is intentionally non-operative in UI1 because SQL
is not retained by the sanitized trace boundary; enabling developer SQL requires a future
audited query-boundary implementation.

No cancellation endpoint is exposed: AgentRunner has no cooperative cancellation token,
and UI1 does not kill tasks or threads unsafely. CORS accepts only the comma-separated
`ANALYTICS_UI_FRONTEND_ORIGINS` setting (default `http://localhost:3000`).
