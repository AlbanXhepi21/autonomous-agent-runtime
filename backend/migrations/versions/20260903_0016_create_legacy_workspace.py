"""create legacy workspace

Revision ID: 20260903_0016
Revises: 20260902_0015
Create Date: 2026-09-03 00:00:00

Step 1 of the tenant-isolation migration ("create or identify a default
tenant for existing data"). Every pre-tenancy row with no reliable ownership
signal (conversations, artifacts, memories, deliveries) is backfilled onto
this one workspace in migration 20260903_0018 -- never guessed onto a real
tenant. Its ID is a fixed, recognizable constant so later migrations in this
sequence can reference it directly without a lookup query.
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260903_0016"
down_revision = "20260902_0015"
branch_labels = None
depends_on = None

#: Fixed, recognizable ID for the one workspace pre-tenancy data is backfilled to.
LEGACY_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"

workspaces_table = sa.table(
    "workspaces",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("slug", sa.String),
    sa.column("logo_ref", sa.Text),
    sa.column("is_active", sa.Boolean),
    sa.column("default_timezone", sa.String),
    sa.column("default_locale", sa.String),
    sa.column("default_currency", sa.String),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    op.bulk_insert(workspaces_table, [{
        "id": LEGACY_WORKSPACE_ID, "name": "Legacy (Pre-Tenancy Data)", "slug": "legacy",
        "logo_ref": None, "is_active": True, "default_timezone": "UTC",
        "default_locale": "en-US", "default_currency": "USD", "created_at": now, "updated_at": now,
    }])


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM workspaces WHERE id = CAST(:id AS uuid)").bindparams(id=LEGACY_WORKSPACE_ID)
    )
