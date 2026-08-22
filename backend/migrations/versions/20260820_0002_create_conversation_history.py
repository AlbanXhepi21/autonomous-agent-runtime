"""create conversation, message, and agent run history

Revision ID: 20260820_0002
Revises: 20260817_0001
Create Date: 2026-08-20 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260820_0002"
down_revision = "20260817_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("conversations", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("title", sa.String(length=255), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_conversations_updated_at", "conversations", ["updated_at"])
    op.create_table("messages", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("role", sa.String(length=16), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("run_id", sa.String(length=255), nullable=True), sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_messages_conversation_created_at", "messages", ["conversation_id", "created_at"])
    op.create_index("ix_messages_run_id", "messages", ["run_id"])
    op.create_table("agent_runs", sa.Column("id", sa.String(length=255), nullable=False), sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("user_message_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("status", sa.String(length=32), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), nullable=True), sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True), sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True), sa.Column("error", sa.Text(), nullable=True), sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["user_message_id"], ["messages.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_agent_runs_conversation_created_at", "agent_runs", ["conversation_id", "created_at"])
    op.create_index("ix_agent_runs_user_message_id", "agent_runs", ["user_message_id"])


def downgrade() -> None:
    op.drop_table("agent_runs")
    op.drop_table("messages")
    op.drop_table("conversations")
