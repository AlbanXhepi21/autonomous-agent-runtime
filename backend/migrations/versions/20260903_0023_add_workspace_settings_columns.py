"""add workspace settings columns

Revision ID: 20260903_0023
Revises: 20260903_0022
Create Date: 2026-09-03 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20260903_0023"
down_revision = "20260903_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workspaces", sa.Column("fiscal_year_start_month", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("workspaces", sa.Column("number_format", sa.String(length=32), nullable=False, server_default="1,234.56"))
    op.add_column("workspaces", sa.Column("date_format", sa.String(length=32), nullable=False, server_default="YYYY-MM-DD"))
    op.add_column("workspaces", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.create_check_constraint(
        "ck_workspaces_fiscal_year_start_month", "workspaces",
        "fiscal_year_start_month >= 1 AND fiscal_year_start_month <= 12",
    )


def downgrade() -> None:
    op.drop_constraint("ck_workspaces_fiscal_year_start_month", "workspaces", type_="check")
    op.drop_column("workspaces", "version")
    op.drop_column("workspaces", "date_format")
    op.drop_column("workspaces", "number_format")
    op.drop_column("workspaces", "fiscal_year_start_month")
