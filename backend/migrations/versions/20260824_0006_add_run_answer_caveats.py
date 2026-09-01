"""persist the limitations an answer stated with each agent run

Revision ID: 20260824_0006
Revises: 20260823_0005
Create Date: 2026-08-24 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260824_0006"
down_revision = "20260823_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("answer_caveats", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_runs", "answer_caveats")
