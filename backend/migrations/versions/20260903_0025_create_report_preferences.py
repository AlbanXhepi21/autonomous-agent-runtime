"""create report preferences

Revision ID: 20260903_0025
Revises: 20260903_0024
Create Date: 2026-09-03 00:00:02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260903_0025"
down_revision = "20260903_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_preferences",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("default_template", sa.String(length=128), nullable=True),
        sa.Column("default_output_format", sa.String(length=8), nullable=True),
        sa.Column("default_theme", sa.String(length=128), nullable=True),
        sa.Column("default_narrative_policy", sa.String(length=32), nullable=True),
        sa.Column("evidence_appendix_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("technical_sql_appendix_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("report_preferences")
