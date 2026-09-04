# Database migrations

## Conventions

Migration files live in `backend/migrations/versions/`, named
`YYYYMMDD_NNNN_description.py`, where `NNNN` is a zero-padded counter that increments
**globally across the whole history**, not per day — several migrations sharing one date
(e.g. `20260903_0016` through `20260903_0026`) still increment continuously. The
`revision` string inside the file is literally this filename prefix (e.g.
`"20260903_0026"`), not an alembic-generated hash.

**Migrations are always hand-written, never generated.** There is no use of `alembic
revision --autogenerate` anywhere in this project's history or documentation — every
migration is authored by copying the structure of a recent one and picking the next
`NNNN`.

## Anatomy of a migration file

```python
"""create audit log

Revision ID: 20260903_0026
Revises: 20260903_0025
Create Date: ...
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260903_0026"
down_revision = "20260903_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_log_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # ...
    )
    op.create_index("ix_audit_log_entries_workspace", "audit_log_entries", ["workspace_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_entries_workspace", table_name="audit_log_entries")
    op.drop_table("audit_log_entries")
```

**Every migration in this repository implements a real `downgrade()` — none are a bare
`pass`.** Where a downgrade genuinely can't restore data (for instance, a backfill
migration), the convention is to implement it anyway and document the limitation in the
function's own docstring rather than leaving it empty:

```python
def downgrade() -> None:
    """Legacy workspace rows created here are intentionally left in place on downgrade --
    removing them could orphan a foreign key that a later migration added."""
```

## Multi-step migrations for a risky schema change

The tenancy rollout (`20260903_0016` through `20260903_0022`) is the reference example
for introducing a NOT NULL, foreign-keyed column across live tables without downtime:

1. **Seed** a default row the backfill can point at (`create_legacy_workspace`).
2. **Add the column nullable** (`add_workspace_id_columns_nullable`).
3. **Backfill** existing rows (`backfill_workspace_ids`).
4. **Validate** — a migration that only reads, aborting the whole migration run if any row
   still lacks the new value (`validate_workspace_backfill`).
5. **Finalize** — drop the old columns, set the new one `NOT NULL`
   (`finalize_workspace_columns`).
6. **Add the foreign key** (`add_workspace_foreign_keys`).
7. **Add indexes** (`add_workspace_indexes`).

Follow this pattern for any similarly risky change rather than a single migration that
adds a NOT NULL column outright.

## Applying migrations

```bash
cd backend
.venv/bin/python -m alembic upgrade head
```

`DATABASE_URL` must be set — `backend/migrations/env.py` raises
`RuntimeError("DATABASE_URL is required to run Alembic migrations")` otherwise,
regardless of which storage backend (`in_memory`/`postgres`) any individual subsystem is
configured to use. Migrations create the schema for the application's own database
(`DATABASE_URL`) only — never the analytics database (`ANALYTICS_DATABASE_URL`), which is
treated as an external, pre-existing source.

## Testing a migration

There is no dedicated "migration test suite" separate from the integration tests — the
`postgres`-marked tests in `backend/tests/integration/` are what exercise a fully migrated
schema, and they assume migrations are already applied (they never create their own
schema):

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agent_test
cd backend && .venv/bin/python -m alembic upgrade head   # against TEST_DATABASE_URL
.venv/bin/python -m pytest
```

Before merging a new migration, at minimum: run `alembic upgrade head` against a fresh
database and confirm it succeeds; run the full `postgres`-marked suite against that
database; and if the migration is a multi-step data migration, verify `downgrade()`
actually reverses what it claims to (or intentionally documents what it doesn't restore).

## Common mistakes

- Writing `down_revision` by hand incorrectly — it must match the previous migration's
  `revision` string exactly, or the migration graph breaks silently until someone runs
  `alembic upgrade head` and gets a confusing multiple-heads error.
- Adding a NOT NULL column directly to a table with existing rows, skipping the seed →
  nullable-add → backfill → validate → finalize sequence — this will fail outright against
  any database with existing data.
- Forgetting that `ANALYTICS_DATABASE_URL` is never touched by these migrations — a
  schema change to the demo/analytics database (if you're the one who owns it) is a
  separate concern entirely.
