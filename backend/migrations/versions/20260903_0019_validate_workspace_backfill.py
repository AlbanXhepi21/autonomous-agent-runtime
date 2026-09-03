"""validate workspace backfill

Revision ID: 20260903_0019
Revises: 20260903_0018
Create Date: 2026-09-03 00:00:03

Step 3 ("validate the backfill"). A real gate, not a comment: counts rows
still missing a workspace assignment on every table this sequence touches
and raises, aborting the upgrade chain before 20260903_0020 ever gets a
chance to add a ``NOT NULL`` constraint that would otherwise fail loudly (or
-- worse, on a table added to this list later without updating this
migration -- silently pass because nothing checked). If this migration ever
fails, the fix is to re-run or extend 20260903_0018's backfill, never to
weaken this check.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260903_0019"
down_revision = "20260903_0018"
branch_labels = None
depends_on = None

_DIRECT_TABLES = ("conversations", "artifacts", "memories", "deliveries")
_CONVERTED_TABLES = ("data_sources", "saved_reports", "scheduled_reports")


def upgrade() -> None:
    bind = op.get_bind()
    failures: list[str] = []
    for table in _DIRECT_TABLES:
        count = bind.execute(
            sa.text(f"SELECT COUNT(*) FROM {table} WHERE workspace_id IS NULL")  # noqa: S608
        ).scalar_one()
        if count:
            failures.append(f"{table}.workspace_id: {count} row(s) still NULL")
    for table in _CONVERTED_TABLES:
        count = bind.execute(
            sa.text(f"SELECT COUNT(*) FROM {table} WHERE workspace_id_new IS NULL")  # noqa: S608
        ).scalar_one()
        if count:
            failures.append(f"{table}.workspace_id_new: {count} row(s) still NULL")

    if failures:
        raise RuntimeError(
            "Workspace backfill validation failed -- refusing to proceed to NOT NULL/foreign-key "
            "migrations with unassigned rows:\n  " + "\n  ".join(failures)
        )


def downgrade() -> None:
    """Nothing to revert -- this migration only ever reads."""
