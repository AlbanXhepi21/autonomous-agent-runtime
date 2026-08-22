"""persist validated interactive chart specifications with each agent run

Revision ID: 20260821_0003
Revises: 20260820_0002
Create Date: 2026-08-21 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260821_0003"
down_revision = "20260820_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("chart_specs", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_runs", "chart_specs")
