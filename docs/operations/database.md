# Database operations

## Two separate databases

`DATABASE_URL` (the application's own state — conversations, runs, memory, artifacts,
identity, tenancy, saved/scheduled reports, audit log) and `ANALYTICS_DATABASE_URL` (the
external, read-only data the agent investigates) are deliberately separate — never point
them at the same database. See [persistence.md](../architecture/persistence.md) and
[data-analysis.md](../architecture/data-analysis.md).

## Migrations

```bash
cd backend && .venv/bin/python -m alembic upgrade head
```

Required unconditionally before starting the API against a new schema — `DATABASE_URL`
must be set even if every individual subsystem is configured `in_memory`, because
`backend/migrations/env.py` requires it to run at all. Full conventions in
[database-migrations.md](../guides/database-migrations.md).

## Connection requirements

Both database URLs use the `postgresql+asyncpg://` scheme — the backend uses `asyncpg`
exclusively. The analytics connection additionally needs, at minimum, a role that can read
the schemas listed in `ANALYTICS_DB_SCHEMA`/a workspace's `allowed_schemas`. Workspace-
connected data sources are separately verified to be read-only at onboarding time (both a
role-privilege check and a live probe) — see
[data-analysis.md](../architecture/data-analysis.md#read-only-database-access) for the one
documented gap: the process-wide demo connection has **no** equivalent role-level check,
only the per-query `SET TRANSACTION READ ONLY`.

## Connection pooling

The application uses SQLAlchemy's async engine directly (`app/db/session.py`); Alembic's
own migration runner uses `NullPool` deliberately (a migration run shouldn't hold a
pooled connection open). There is no separate connection-pooler (PgBouncer or similar)
configuration shipped with this repository — if your deployment needs one, it sits outside
what this codebase configures, transparently in front of `DATABASE_URL`/
`ANALYTICS_DATABASE_URL`.

## Schema ownership

Migrations own the application database's schema completely — tables are never created at
process startup, only by `alembic upgrade head`. The analytics database's schema is owned
by whoever populates it (see [local-development.md](../getting-started/local-development.md)
for the companion sample-data generator) — this application only ever reads it via schema
reflection, never modifies its structure.

## Backend selection per subsystem

`MEMORY_BACKEND`, `ARTIFACT_BACKEND`, `IDENTITY_BACKEND`, `TENANCY_BACKEND` each
independently select `in_memory` or `postgres` (see
[configuration.md](../getting-started/configuration.md)). All four defaulting to
`in_memory` is appropriate for local development only — every one of them loses its state
on process restart in that mode. For any deployment meant to persist across a restart, set
all four to `postgres` explicitly.

## Monitoring database health

Nothing in this repository monitors database connectivity, query latency, or connection
pool saturation — see [observability.md](observability.md) for what is and isn't
instrumented. If you need this, it must come from your database provider's own tooling or
external monitoring pointed at PostgreSQL directly; there is no in-application metric for
it.
