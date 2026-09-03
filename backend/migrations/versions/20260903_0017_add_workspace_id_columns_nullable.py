"""add workspace_id columns (nullable)

Revision ID: 20260903_0017
Revises: 20260903_0016
Create Date: 2026-09-03 00:00:01

Adds the new tenant-scoping columns everywhere they're needed, all still
nullable -- a nullable column add is instant and safe on a live table.
Nothing reads or requires these columns yet; that starts in
20260903_0018 (backfill) and is only enforced from 20260903_0019 onward.

``conversations``/``artifacts``/``memories``/``deliveries`` get a direct
``workspace_id`` for the first time. ``data_sources``/``saved_reports``/
``scheduled_reports`` already have a plain string ``workspace_id`` column;
``workspace_id_new`` is added alongside it so the backfill migration can
populate a real foreign key without disturbing the column every existing
route still reads until the cutover in 20260903_0020.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260903_0017"
down_revision = "20260903_0016"
branch_labels = None
depends_on = None

_DIRECT_TABLES = ("conversations", "artifacts", "memories", "deliveries")
_CONVERTED_TABLES = ("data_sources", "saved_reports", "scheduled_reports")


def upgrade() -> None:
    for table in _DIRECT_TABLES:
        op.add_column(table, sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True))
    for table in _CONVERTED_TABLES:
        op.add_column(table, sa.Column("workspace_id_new", postgresql.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    for table in _CONVERTED_TABLES:
        op.drop_column(table, "workspace_id_new")
    for table in _DIRECT_TABLES:
        op.drop_column(table, "workspace_id")
