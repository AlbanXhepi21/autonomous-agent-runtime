# Production readiness checklist

The project's own `README.md` states plainly: *"This project is under active development.
It is not yet intended for unsupervised production use, particularly for tools capable of
modifying files, executing code, accessing external systems, or performing other
sensitive actions."* Treat this checklist as what to verify and accept, consciously, if
you deploy anyway — not as a guarantee everything below is solved.

## Infrastructure

- [ ] PostgreSQL provisioned for `DATABASE_URL`, migrated (`alembic upgrade head`)
- [ ] PostgreSQL provisioned for `ANALYTICS_DATABASE_URL`, schema populated (see
      [local-development.md](../getting-started/local-development.md))
- [ ] Backend and frontend processes running under a real supervisor (this repository
      ships neither a Dockerfile nor a supervisor config — see
      [deployment.md](deployment.md))
- [ ] Scheduled-report worker running, if saved/scheduled reports are used
- [ ] Artifact retention worker running, if artifact expiry matters to you
- [ ] Backups configured externally (see [backups-and-retention.md](backups-and-retention.md)
      — nothing in-repo does this)

## Configuration

- [ ] `SECURITY_ENVIRONMENT` set explicitly and deliberately — understand its near-total
      lockdown effect before setting `production` (see
      [limitations.md](../reference/limitations.md#the-production-security-environment-is-a-near-total-kill-switch-not-a-tightening))
- [ ] `MEMORY_BACKEND`, `ARTIFACT_BACKEND`, `IDENTITY_BACKEND`, `TENANCY_BACKEND` all set
      to `postgres` (not the `in_memory` defaults, which lose all state on restart)
- [ ] `AUTH_COOKIE_SECURE` confirmed true in practice (verify explicitly if
      `SECURITY_ENVIRONMENT` isn't the literal string `production`, since only that exact
      value forces it)
- [ ] `PUBLIC_API_BASE_URL`, `APP_BASE_URL`, `ANALYTICS_UI_FRONTEND_ORIGINS` set to real,
      non-localhost values
- [ ] `DATA_SOURCE_ENCRYPTION_KEY` generated and stored durably (rotating it invalidates
      every stored data-source password)
- [ ] `SMTP_PASSWORD`/`GITHUB_TOKEN` exported as real process environment variables, not
      placed only in `.env` (they bypass the usual settings loader — see
      [configuration.md](../getting-started/configuration.md))
- [ ] `OPENAI_API_KEY` set (nothing enforces this at startup; a run will simply fail on
      its first model call otherwise)

## Security posture accepted

- [ ] Aware that prompt-injection defenses are heuristic/diagnostic, not a solved
      guarantee
- [ ] Aware that the restricted Python/command sandboxes are process isolation, not a
      hardened hostile-code boundary — human approval on those capabilities is the real
      control
- [ ] Aware `POST /api/v1/invitations/accept` currently lacks CSRF protection
- [ ] No MFA/SSO available for authentication — accepted, or built separately, before
      exposing this to users who need it
- [ ] Reviewed [security.md](security.md) and
      [security-boundaries.md](../architecture/security-boundaries.md) in full

## Observability accepted

- [ ] No external metrics/tracing integration exists — log aggregation is your own
      responsibility (see [observability.md](observability.md))
- [ ] Aware that a server restart loses all in-flight run traces (bounded to the most
      recent 1,000, in-memory only) — only the denormalized run summary survives

## Functional limitations accepted

- [ ] Only PostgreSQL data sources are supported — no CSV upload, no warehouse connectors
- [ ] `web_search` is unimplemented and unregistered — any specialist or skill expecting
      it to work will not function as written
- [ ] 9 of 28 semantic metrics are documentation-only (agent-authored SQL, not a
      recomputable statement)
- [ ] The agent tends to produce one display per run in practice, despite a coded ceiling
      of 8 — reports may print "This analysis produced no charts"
- [ ] Recursive delegation and automatic specialist routing are intentionally absent —
      delegation is always a single, explicit, model-selected choice
- [ ] Full list: [limitations.md](../reference/limitations.md)

## Testing before go-live

- [ ] Full backend suite green, including the `postgres`-marked tests against a real,
      migrated database (see [testing.md](../guides/testing.md))
- [ ] `frontend/openapi.json` regenerated and committed if any backend API changed
      (`npm run gen:api`), and `test_openapi_snapshot.py` passes
- [ ] `scripts.preview_reports` run to visually check every template you intend to use —
      automated text assertions do not catch layout regressions
- [ ] Manual scenario walkthrough via
      `python -m scripts.run_agent_scenarios --all` against the deployed API

## What this checklist does not cover

This repository has no CI, so none of the above is enforced automatically on merge — see
[pull-requests.md](../contributing/pull-requests.md) for what a human reviewer should
verify by hand in its place.
