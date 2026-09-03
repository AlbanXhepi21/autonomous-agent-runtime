"""finalize workspace columns

Revision ID: 20260903_0020
Revises: 20260903_0019
Create Date: 2026-09-03 00:00:04

Step 4 ("add non-null constraints after validation") -- reached only if
20260903_0019 passed. For the three tables converted from a plain string:
drops the old ``workspace_id`` string column and renames ``workspace_id_new``
into its place. For every one of the seven tables in this sequence, sets
``workspace_id NOT NULL`` now that every row is known to have one.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260903_0020"
down_revision = "20260903_0019"
branch_labels = None
depends_on = None

_DIRECT_TABLES = ("conversations", "artifacts", "memories", "deliveries")
_CONVERTED_TABLES = ("data_sources", "saved_reports", "scheduled_reports")
_OLD_STRING_LENGTHS = {"data_sources": 128, "saved_reports": 128, "scheduled_reports": 128}


def upgrade() -> None:
    for table in _CONVERTED_TABLES:
        op.drop_column(table, "workspace_id")
        op.alter_column(table, "workspace_id_new", new_column_name="workspace_id")
    for table in (*_DIRECT_TABLES, *_CONVERTED_TABLES):
        op.alter_column(table, "workspace_id", nullable=False)


def downgrade() -> None:
    """Schema-only reversal. The original workspace_id *string values* on the
    three converted tables are not recoverable here -- they were dropped in
    upgrade() -- so this restores the column shape (nullable string), not
    its former content.
    """

    for table in (*_DIRECT_TABLES, *_CONVERTED_TABLES):
        op.alter_column(table, "workspace_id", nullable=True)
    for table in _CONVERTED_TABLES:
        op.alter_column(table, "workspace_id", new_column_name="workspace_id_new")
        op.add_column(
            table, sa.Column("workspace_id", sa.String(length=_OLD_STRING_LENGTHS[table]), nullable=True)
        )
