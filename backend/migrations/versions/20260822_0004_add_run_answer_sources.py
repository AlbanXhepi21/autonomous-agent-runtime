"""persist the evidence an answer cited with each agent run

Revision ID: 20260822_0004
Revises: 20260821_0003
Create Date: 2026-08-22 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260822_0004"
down_revision = "20260821_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("answer_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_runs", "answer_sources")
