"""extend data sources with lifecycle, ownership, and soft-delete columns

Revision ID: 20260905_0027
Revises: 20260903_0026
Create Date: 2026-09-05 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20260905_0027"
down_revision = "20260903_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("data_sources", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "data_sources", sa.Column("engine", sa.String(length=32), nullable=False, server_default="postgresql"),
    )
    op.add_column(
        "data_sources", sa.Column("environment", sa.String(length=16), nullable=False, server_default="development"),
    )
    op.add_column(
        "data_sources", sa.Column("connection_timeout_seconds", sa.Float(), nullable=False, server_default="10"),
    )
    op.add_column("data_sources", sa.Column("source_timezone", sa.String(length=64), nullable=True))
    op.add_column("data_sources", sa.Column("last_error_category", sa.String(length=32), nullable=True))
    op.add_column(
        "data_sources", sa.Column("last_successful_connection_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Never backfilled with a guess -- NULL on every pre-existing row means
    # "created before this column existed," not "created by no one."
    op.add_column("data_sources", sa.Column("created_by", sa.String(length=128), nullable=True))
    op.add_column("data_sources", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("data_sources", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_data_sources_workspace_deleted", "data_sources", ["workspace_id", "deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_data_sources_workspace_deleted", table_name="data_sources")
    op.drop_column("data_sources", "deleted_at")
    op.drop_column("data_sources", "version")
    op.drop_column("data_sources", "created_by")
    op.drop_column("data_sources", "last_successful_connection_at")
    op.drop_column("data_sources", "last_error_category")
    op.drop_column("data_sources", "source_timezone")
    op.drop_column("data_sources", "connection_timeout_seconds")
    op.drop_column("data_sources", "environment")
    op.drop_column("data_sources", "engine")
    op.drop_column("data_sources", "description")
