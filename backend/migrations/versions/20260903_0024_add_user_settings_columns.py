"""add user settings columns

Revision ID: 20260903_0024
Revises: 20260903_0023
Create Date: 2026-09-03 00:00:01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260903_0024"
down_revision = "20260903_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("pending_email", sa.String(length=320), nullable=True))
    op.add_column("users", sa.Column("preferred_timezone", sa.String(length=64), nullable=False, server_default="UTC"))
    op.add_column("users", sa.Column("preferred_locale", sa.String(length=16), nullable=False, server_default="en-US"))
    op.add_column("users", sa.Column("profile_image_artifact_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("users", sa.Column("profile_image_workspace_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_users_profile_image_workspace_id", "users", "workspaces",
        ["profile_image_workspace_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_profile_image_workspace_id", "users", type_="foreignkey")
    op.drop_column("users", "profile_image_workspace_id")
    op.drop_column("users", "profile_image_artifact_id")
    op.drop_column("users", "preferred_locale")
    op.drop_column("users", "preferred_timezone")
    op.drop_column("users", "pending_email")
