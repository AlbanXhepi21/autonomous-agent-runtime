# Migration conventions

Load this only for application-database schema changes.

- Migrations are hand-written in `backend/migrations/versions/`, named `YYYYMMDD_NNNN_description.py`; the revision is the filename prefix and `NNNN` increments globally.
- Inspect with `cd backend && .venv/bin/python -m alembic heads`; apply with `cd backend && .venv/bin/python -m alembic upgrade head`. `DATABASE_URL` is required.
- Every migration has a real `downgrade()`. For risky populated tables, use seed → nullable add → backfill → validate → finalize → foreign key/index steps.
- Migrations affect the application database only, never `ANALYTICS_DATABASE_URL`. Postgres-marked tests require migrated `TEST_DATABASE_URL` and do not create their own schema.

Read [database migrations](../../../../docs/guides/database-migrations.md) before assigning a revision or designing a data migration.
