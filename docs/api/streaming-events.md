# API: Streaming events (SSE)

```http
GET /api/v1/workspaces/{workspace_id}/analytics/runs/{run_id}/events
Accept: text/event-stream
Last-Event-ID: <optional, for reconnection>
```

## Wire format

Named SSE events, each with an `id:`, an `event:` type, and a JSON `PublicRunEvent` body:

```
id: 7
event: sql.query_completed
data: {"id": "7", "run_id": "...", "type": "sql.query_completed", "timestamp": "...", "data": {...}}

: keepalive

id: 8
event: chart.created
data: {"id": "8", "run_id": "...", "type": "chart.created", "timestamp": "...", "data": {...}}
```

A blank `: keepalive` comment line is sent roughly every 250ms while nothing new is
available, to keep the connection alive through intermediate proxies.

## The complete event vocabulary (24 types)

Exactly what the backend can ever project — verified by cross-referencing the frontend's
own event-type list against the backend's internal-to-public projection map, which are
kept in exact agreement:

```
run.started              run.completed            run.failed
agent.started             agent.completed
skill.loaded
schema.tables_listed      schema.table_described
sql.query_started         sql.query_completed       sql.query_failed       sql.query_rejected
python.analysis_started    python.analysis_completed
artifact.created           chart.created             report.created
plan.updated
delegation.started         delegation.completed
tool.started                tool.completed            tool.failed
security.policy_evaluated
```

`agent.started`/`agent.completed` are synthesized by the projection layer itself (wrapping
the internal run-start/run-finish trace events) — every other type is a direct 1:1
projection of an internal trace event type. No internal event type is ever projected that
isn't in this list; this is the complete, closed vocabulary a client will ever see.

## Lifecycle

1. Connect immediately after `POST .../runs` returns its `run_id`.
2. Events arrive in order as the run progresses.
3. **The stream closes automatically** the moment the run reaches a terminal state — the
   server returns from the generator right after emitting the terminal `run.completed` or
   `run.failed` event. There is no explicit "end of stream" event separate from those two.
4. A standard browser `EventSource` reconnects automatically on a dropped connection,
   sending `Last-Event-ID` itself — the frontend does not manage this by hand.

## Reconnection is process-local only

Run state lives in memory on the API process. If the connection drops and reconnects
**within the same server process**, the server resumes yielding events after the last
delivered ID. If the server process has since restarted, the run's trace no longer exists
and the endpoint responds `410 {"code": "trace_expired", ...}` instead of resuming — there
is no durable trace to reconnect to (see
[persistence.md](../architecture/persistence.md#messages-and-traces)).

## Replaying past events

```http
GET /api/v1/workspaces/{workspace_id}/analytics/runs/{run_id}/events/history
```

Returns the same full projected event list as a plain, unpaginated `{"items": [...]}` —
used by the frontend to hydrate a run restored from conversation history, not for
live-stream gap-filling (that's what `Last-Event-ID` reconnection is for, and it only
works within one server process — see above).
