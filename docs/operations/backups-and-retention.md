# Backups and retention

## Backups: not provided by this repository

**There is no backup tooling of any kind in this codebase** — no scheduled `pg_dump`, no
snapshot automation, no restore script. Verified by direct search: no reference to
`pg_dump`, `pg_basebackup`, WAL archiving, or any backup vendor anywhere in `backend/` or
`scripts/`. Backing up `DATABASE_URL` (and, if you consider it your responsibility rather
than upstream, `ANALYTICS_DATABASE_URL`) is entirely an external operational concern — use
your PostgreSQL provider's standard backup mechanism (managed snapshots, `pg_dump` on a
schedule, WAL-based point-in-time recovery) exactly as you would for any other PostgreSQL
database. Nothing about this application's schema requires special backup handling beyond
standard PostgreSQL practice.

Artifact **bytes** (as opposed to their database rows) live on local disk under the
workspace root (`AGENT_WORKSPACE_ROOT`) — back this up as a filesystem, alongside the
database, if artifact durability across a disaster matters to you. There is no object
storage integration (S3-compatible or otherwise) to offload this to.

## Artifact retention: implemented, but not self-starting

The retention sweep itself is real and working —
`backend/scripts/run_artifact_retention.py` claims expired, `standard`-policy, `READY`
artifacts (safely across multiple concurrent worker processes, via row-level locking),
deletes their bytes, and marks the row `DELETED` with a full audit trail retained. This
corrects a stale claim still present in the root `README.md` — see
[limitations.md](../reference/limitations.md#retention-sweeper-status).

**Nothing in this repository starts this worker automatically.** Run it under your own
schedule:

```bash
cd backend && .venv/bin/python -m scripts.run_artifact_retention --interval-seconds 3600
```

or invoke `--once` from an external cron/systemd-timer if you'd rather not run it as a
long-lived process.

Retention policy per artifact is one of `standard` (subject to expiry), `legal_hold`, or
`permanent` — the sweep's own database query excludes the latter two, so they cannot be
deleted even by direct invocation of the worker. `SCHEDULED_REPORT_ARTIFACT_RETENTION_DAYS`
(default 90) sets the expiry window for artifacts a *scheduled* report produces; ad-hoc,
manually published artifacts get no expiry by default.

## Session and token retention

Session, password-reset, and email-verification records accumulate in their respective
tables indefinitely — there is no sweep for expired sessions or spent/expired tokens in
this repository (distinct from artifact retention, which does have a worker). An expired
or revoked session is rejected at validation time regardless of whether its row still
exists, so this is a storage-growth concern, not a security one, but there is currently no
built-in cleanup job for it.

## Trace retention

Traces are bounded in-memory (most recent 1,000, oldest evicted first) and are never
durable regardless of retention policy — see
[observability.md](observability.md#traces). There is nothing to back up or retain here
by design; if you need durable run history, rely on the denormalized fields already
persisted on the run record (`answer_sources`, `chart_specs`, `answer_caveats`, `metrics`,
final answer text), not the trace.

## Memory retention

Agent memory (when `MEMORY_BACKEND=postgres`) accumulates indefinitely — no automatic
pruning or consolidation exists (see [memory.md](../concepts/memory.md)). If unbounded
memory growth matters for your deployment, this is an area you'd need to build; it isn't
handled today.
