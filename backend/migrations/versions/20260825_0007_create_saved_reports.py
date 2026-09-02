"""create saved report definitions and their execution history

Revision ID: 20260825_0007
Revises: 20260824_0006
Create Date: 2026-08-25 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260825_0007"
down_revision = "20260824_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saved_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("owner", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("template_id", sa.String(length=64), nullable=False),
        sa.Column("template_version", sa.String(length=32), nullable=False),
        sa.Column("metric_requests", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("default_period", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("narrative_policy", sa.String(length=32), nullable=False),
        # Denormalised at save time so the original narrative survives even if
        # the conversation it came from is later deleted -- the same reasoning
        # already applied to answer_sources on agent_runs.
        sa.Column("seed_run_id", sa.String(length=255), nullable=True),
        sa.Column("seed_narrative", sa.Text(), nullable=True),
        sa.Column("seed_narrative_period", sa.String(length=160), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_saved_reports_workspace_status", "saved_reports", ["workspace_id", "status", "updated_at"])

    op.create_table(
        "saved_report_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "saved_report_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("saved_reports.id", ondelete="RESTRICT"), nullable=False,
        ),
        # The runtime run ID this execution minted its rerun evidence and any
        # artifacts under; also the key artifacts are looked up by.
        sa.Column("run_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("resolved_period_start", sa.Date(), nullable=True),
        sa.Column("resolved_period_end", sa.Date(), nullable=True),
        sa.Column("formats", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_saved_report_executions_report_created_at", "saved_report_executions",
        ["saved_report_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_saved_report_executions_report_created_at", table_name="saved_report_executions")
    op.drop_table("saved_report_executions")
    op.drop_index("ix_saved_reports_workspace_status", table_name="saved_reports")
    op.drop_table("saved_reports")
