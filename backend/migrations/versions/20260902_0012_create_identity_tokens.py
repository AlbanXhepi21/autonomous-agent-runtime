"""create identity tokens

Revision ID: 20260902_0012
Revises: 20260902_0011
Create Date: 2026-09-02 00:00:02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260902_0012"
down_revision = "20260902_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identity_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        # "password_reset" | "email_verification" -- see app.identity.contracts.TokenPurpose.
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_identity_tokens_token_hash", "identity_tokens", ["token_hash"], unique=True)
    op.create_index("ix_identity_tokens_user_purpose", "identity_tokens", ["user_id", "purpose"])


def downgrade() -> None:
    op.drop_index("ix_identity_tokens_user_purpose", table_name="identity_tokens")
    op.drop_index("ix_identity_tokens_token_hash", table_name="identity_tokens")
    op.drop_table("identity_tokens")
