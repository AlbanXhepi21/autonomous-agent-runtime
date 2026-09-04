---
name: database-migration
description: Design, create, and verify a focused autonomous-agent Alembic migration for application-schema changes, SQLAlchemy persistence changes, constraints, indexes, data backfills, or tenant-ownership changes. Do not use for external analytics-database changes, application behavior with no schema change, or a conceptual Alembic explanation.
---

# Database migration

## Workflow

Follow this order:

```text
Inspect current migration heads
→ inspect model/repository usage
→ design upgrade and rollback
→ create one focused migration
→ apply against test database
→ verify model and repository behavior
→ test upgrade/downgrade where supported
→ inspect generated SQL/risk
```

1. Inspect the current Alembic head with `cd backend && .venv/bin/python -m alembic heads`, then inspect the latest migration and the affected persistence records, stores, and tests. Never guess `down_revision`.
2. Design one focused, hand-written migration and its real rollback before editing. Do not modify an already-applied migration unless project policy explicitly authorizes it; do not use Alembic autogeneration.
3. For populated data, add nullable state, backfill and validate it, then add non-null constraints or foreign keys. Preserve workspace scoping and add indexes only for verified access patterns.
4. Apply with `cd backend && .venv/bin/python -m alembic upgrade head` against a fresh test database. Verify affected model/store behavior with the relevant Postgres-marked integration tests.
5. Test downgrade where the change supports it. Inspect the operations and report table-rewrite, lock-duration, data-loss, or deploy-order risks.

## Required checks

- Read [migration conventions](references/migration-conventions.md) before choosing IDs, dependencies, or validation commands.
- Read [tenant isolation](references/tenant-isolation.md) for workspace ownership, foreign keys, backfills, or scoped-store changes.
- Read [repository boundaries](references/repository-boundaries.md) only when persistence changes also expose a route or public contract.
- Read [testing map](references/testing-map.md) when database configuration or integration coverage is needed.

## Stop and ask

- A required data meaning, backfill rule, retention rule, or deploy sequence is unresolved.
- The operation would delete production data, rewrite a large table, or hold a long lock without explicit authorization.
- A fresh database, `DATABASE_URL`, or required test fixture is unavailable; report the exact missing prerequisite instead of simulating migration success.

## Completion report

State: migration ID and parent; upgrade/downgrade behavior; backfill and index decisions; database/tests run; lock/data/deploy risks; skipped checks or blockers.
