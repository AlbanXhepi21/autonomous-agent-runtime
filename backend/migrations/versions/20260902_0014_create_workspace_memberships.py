"""create workspace memberships

Revision ID: 20260902_0014
Revises: 20260902_0013
Create Date: 2026-09-02 00:00:04
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260902_0014"
down_revision = "20260902_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint(
        "uq_workspace_membership_user_workspace", "workspace_memberships", ["user_id", "workspace_id"],
    )
    op.create_index("ix_workspace_memberships_workspace", "workspace_memberships", ["workspace_id"])
    op.create_index("ix_workspace_memberships_user", "workspace_memberships", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_workspace_memberships_user", table_name="workspace_memberships")
    op.drop_index("ix_workspace_memberships_workspace", table_name="workspace_memberships")
    op.drop_constraint("uq_workspace_membership_user_workspace", "workspace_memberships", type_="unique")
    op.drop_table("workspace_memberships")
