"""create workspace data sources and their governed catalog

Revision ID: 20260827_0009
Revises: 20260826_0008
Create Date: 2026-08-27 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260827_0009"
down_revision = "20260826_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False, server_default="5432"),
        sa.Column("database_name", sa.String(length=128), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=False),
        # Ciphertext only -- see app.datasources.encryption. Never selected
        # back into an API response.
        sa.Column("encrypted_password", sa.Text(), nullable=False),
        sa.Column("ssl_mode", sa.String(length=16), nullable=False, server_default="require"),
        sa.Column("allowed_schemas", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("statement_timeout_seconds", sa.Float(), nullable=False, server_default="15"),
        sa.Column("max_result_rows", sa.Integer(), nullable=False, server_default="5000"),
        sa.Column("max_result_bytes", sa.Integer(), nullable=False, server_default="1000000"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("health_status", sa.String(length=16), nullable=False, server_default="unknown"),
        sa.Column("last_connection_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_connection_error", sa.Text(), nullable=True),
        sa.Column("last_profiled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_data_sources_workspace", "data_sources", ["workspace_id"])
    op.create_index("ix_data_sources_workspace_status", "data_sources", ["workspace_id", "status"])

    op.create_table(
        "data_source_tables",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "data_source_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("schema_name", sa.String(length=128), nullable=False),
        sa.Column("technical_name", sa.String(length=128), nullable=False),
        sa.Column("business_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("grain", sa.String(length=500), nullable=True),
        sa.Column("freshness_column", sa.String(length=128), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("approved_by", sa.String(length=128), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("data_source_id", "schema_name", "technical_name", name="uq_data_source_table"),
    )
    op.create_index("ix_data_source_tables_source_active", "data_source_tables", ["data_source_id", "active"])

    op.create_table(
        "data_source_columns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "data_source_table_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_source_tables.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("technical_name", sa.String(length=128), nullable=False),
        sa.Column("data_type", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="other"),
        sa.Column("sensitivity", sa.String(length=32), nullable=False, server_default="internal"),
        sa.Column("excluded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("example_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("data_source_table_id", "technical_name", name="uq_data_source_column"),
    )

    op.create_table(
        "data_source_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "data_source_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("source_table", sa.String(length=128), nullable=False),
        sa.Column("source_column", sa.String(length=128), nullable=False),
        sa.Column("target_table", sa.String(length=128), nullable=False),
        sa.Column("target_column", sa.String(length=128), nullable=False),
        sa.Column("cardinality", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("discovery_method", sa.String(length=16), nullable=False),
        sa.Column("approval_status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("approved_by", sa.String(length=128), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_data_source_relationships_source_status", "data_source_relationships",
        ["data_source_id", "approval_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_data_source_relationships_source_status", table_name="data_source_relationships")
    op.drop_table("data_source_relationships")

    op.drop_table("data_source_columns")

    op.drop_index("ix_data_source_tables_source_active", table_name="data_source_tables")
    op.drop_table("data_source_tables")

    op.drop_index("ix_data_sources_workspace_status", table_name="data_sources")
    op.drop_index("ix_data_sources_workspace", table_name="data_sources")
    op.drop_table("data_sources")
