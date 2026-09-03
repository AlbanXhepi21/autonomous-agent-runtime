"""create audit log

Revision ID: 20260903_0026
Revises: 20260903_0025
Create Date: 2026-09-03 00:00:03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260903_0026"
down_revision = "20260903_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_log_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("event_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_log_entries_workspace", "audit_log_entries", ["workspace_id", "created_at"])
    op.create_index("ix_audit_log_entries_actor", "audit_log_entries", ["actor_user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_entries_actor", table_name="audit_log_entries")
    op.drop_index("ix_audit_log_entries_workspace", table_name="audit_log_entries")
    op.drop_table("audit_log_entries")
