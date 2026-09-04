# Deployment

This documents the **only** deployment path this repository actually supports: a
FastAPI process, a Next.js process, and PostgreSQL, run by whatever process supervisor you
choose. **There is no Dockerfile, no `docker-compose.yml`, no Kubernetes manifest, no
Redis, and no cloud object storage integration anywhere in this repository** — verified by
direct filesystem search, not merely undocumented. Do not introduce any of these as if
they were already supported; if you adopt one, this page (and
[production-checklist.md](production-checklist.md)) needs updating to match reality.

## Required services

| Service | Required? | Notes |
|---|---|---|
| PostgreSQL (application database) | Yes, for any durable deployment | `DATABASE_URL` — needed to run migrations and for any `postgres`-backed subsystem |
| PostgreSQL (analytics database) | Yes, for analysis to function at all | `ANALYTICS_DATABASE_URL` — a separate database/server from the above |
| OpenAI API access | Yes, for any real agent run | `OPENAI_API_KEY` |
| SMTP server | Only if using email delivery | `SMTP_HOST`/`SMTP_FROM_ADDRESS` (and `SMTP_PASSWORD`, exported as a real environment variable — see [configuration.md](../getting-started/configuration.md)) |
| Anything else (Redis, a queue, object storage, a reverse-proxy-specific feature) | **No** — not implemented | |

## Processes to run

1. **Backend API** — `uvicorn app.main:create_app --factory` (no `--reload` in
   production; `backend/scripts/run_api_dev.sh` is a *development* convenience script that
   hardcodes `--reload`, `127.0.0.1`, and port `8000` — use a production-appropriate
   invocation directly instead of that script).
2. **Frontend** — `next build && next start` (there is no dedicated production start
   script beyond what `next` itself provides via its CLI).
3. **Scheduled-report worker** — `python -m scripts.run_scheduled_reports
   --interval-seconds N`, only if you use saved/scheduled reports. Nothing starts this
   automatically.
4. **Artifact retention worker** — `python -m scripts.run_artifact_retention
   --interval-seconds N`, if you want expired artifacts actually swept (see
   [backups-and-retention.md](backups-and-retention.md)). Nothing starts this
   automatically either.

Both worker scripts are safe to run as more than one process against the same database —
they use row-level claim locking (`SELECT ... FOR UPDATE SKIP LOCKED`) specifically so a
restart or a brief overlap during a deploy doesn't double-process anything.

## Process supervision

This repository does not prescribe or ship a specific supervisor — no systemd unit files,
no Procfile, no PM2 config. Use whatever your environment already standardizes on
(systemd, a container platform's own process management, a managed PaaS) to keep the API,
the frontend, and the two worker scripts running and restarted on failure. Whatever you
choose, the same principle applies to all four: no in-repo mechanism restarts them for
you.

## Production configuration

At minimum, beyond local defaults (see
[configuration.md](../getting-started/configuration.md) for the complete variable
reference):

- `SECURITY_ENVIRONMENT=production` — **read this carefully before setting it.** It is
  not a mild tightening; it denies almost every read-only and analytics tool outright
  (see [limitations.md](../reference/limitations.md#the-production-security-environment-is-a-near-total-kill-switch-not-a-tightening)).
  Confirm this is genuinely the behavior you want before deploying with it set.
- `MEMORY_BACKEND=postgres`, `ARTIFACT_BACKEND=postgres`, `IDENTITY_BACKEND=postgres`,
  `TENANCY_BACKEND=postgres` — the `in_memory` defaults lose all state on every restart;
  appropriate for local development only.
- `AUTH_COOKIE_SECURE` — note this is only *forced* true by the literal value
  `SECURITY_ENVIRONMENT=production`; `staging`/`unknown` do not force it, so set it
  explicitly if you're not using the literal `production` value.
- `PUBLIC_API_BASE_URL` / `APP_BASE_URL` — set to your real public URLs; these are used to
  build links inside delivered emails/webhooks and password-reset/verification emails.
- `ANALYTICS_UI_FRONTEND_ORIGINS` — set to your real frontend origin(s); CORS never
  defaults to a wildcard.
- `DATA_SOURCE_ENCRYPTION_KEY` — required before any workspace can save a connected data
  source; generate once and treat rotation as invalidating every stored data-source
  password.

## Database migrations

Run once per deployment, before starting the API against a new schema version:

```bash
cd backend && .venv/bin/python -m alembic upgrade head
```

See [database.md](database.md) and [database-migrations.md](../guides/database-migrations.md).

## Rollback

There is no rollback tooling in this repository — no blue/green scripting, no automated
migration-downgrade-on-deploy-failure. A rollback means, in order: stop routing traffic to
the new version, revert the deployed code to the previous known-good commit/artifact, and
— only if the new version's migrations are incompatible with the old code — run `alembic
downgrade <previous_revision>` against the database. Every migration in this repository
implements a real `downgrade()` (see
[database-migrations.md](../guides/database-migrations.md)), but downgrading a
data-backfill migration does not restore data it deleted or transformed — read the
specific migration's own docstring before relying on its downgrade to be lossless.

## Health checks

There is no dedicated `/health` endpoint. Use:

- `GET /api/v1/config` — unauthenticated, returns `{"developer_mode": bool}`. The
  simplest true liveness check: if this responds, the process is up and settings loaded
  successfully.
- `GET /openapi.json` — confirms the app object built correctly (routes registered,
  schema generation succeeds).

Neither of these checks the database connection. There is no built-in readiness probe
that verifies `DATABASE_URL`/`ANALYTICS_DATABASE_URL` connectivity — if you need that,
it must be added or checked externally (e.g. your supervisor probing Postgres directly).
