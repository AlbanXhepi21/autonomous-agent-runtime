# Observability

**No external observability system is integrated anywhere in this codebase** — no
OpenTelemetry, no Prometheus, no Sentry, no structured-logging shipping service. Verified
by grepping every backend package and `backend/pyproject.toml` for these and related
packages: zero matches. Everything described below is custom and in-process.

## Logging

`backend/app/core/logging.py` provides hand-rolled structured logging
(`configure_logging`, `log_event`), configured once at process startup from `LOG_LEVEL`
and `LOG_FORMAT` (`pretty` or otherwise — see
[configuration.md](../getting-started/configuration.md)). It also carries the
secret-redaction mechanism: `register_secret_value()` and `redact_secret_text()` scrub
known resolved secrets and pattern-match common credential shapes (API keys, Bearer
tokens, PEM headers) out of anything logged through `safe_log_value`/`safe_error_message`.
This depends on call sites actually using those helpers — there is no single centralized
enforcement point guaranteeing every log call is routed through redaction. A second,
independent redaction implementation (`SecretRedactor` in
`backend/app/security/credentials.py`) exists doing the same job by a different code
path — see [security-boundaries.md](../architecture/security-boundaries.md).

Logs go to stdout/stderr (standard Python logging configuration) — there is no built-in
log shipping to any external system. Route them wherever your deployment already
collects process output.

## Metrics

There is no metrics-collection library or exported metrics endpoint (no `/metrics`, no
StatsD/Prometheus client). The closest thing to metrics is
`backend/app/observability/run_metrics.py`'s `SystemRunMetrics`/`aggregate_run_metrics()`
— a custom, in-process rollup of a single run's token usage, cost, and duration, surfaced
through the API (`RunResponse.metrics`), not exported for external scraping.

## Traces

A custom, in-process tracing system exists — `RunTrace`/`TraceEvent`
(`backend/app/observability/events.py`), 43 distinct event types covering the full
run/LLM/tool/memory/delegation/security/approval/artifact/database-query/analytics-python/
chart/report/plan lifecycle. **This is not durable and does not integrate with any
external tracing backend.** The only concrete store is `InMemoryTraceStore`, explicitly
documented as process-local, bounded to the most recent 1,000 traces, lost on restart. See
[persistence.md](../architecture/persistence.md#messages-and-traces) and
[limitations.md](../reference/limitations.md).

A run's trace is exposed via `GET /api/v1/workspaces/{workspace_id}/runs/{run_id}/trace`
and, live, via the SSE event stream (see [streaming-events.md](../api/streaming-events.md))
— these are the only ways to observe trace data; there is no export path to an external
observability platform.

## What operating this system without external tooling means in practice

- You cannot query "what happened in run X" after a server restart beyond what's
  persisted on the run record (`answer_sources`, `chart_specs`, `answer_caveats`,
  `metrics`, the final answer text) — the fine-grained trace is gone.
- There is no alerting built in — error rates, approval-queue backlogs, and worker-script
  health all require external monitoring pointed at whatever your logs or health-check
  endpoint expose.
- If you need durable tracing or metrics dashboards, they must be built by adding a real
  backend behind the existing `TraceStore` protocol / by shipping logs elsewhere — neither
  currently exists in this repository.
