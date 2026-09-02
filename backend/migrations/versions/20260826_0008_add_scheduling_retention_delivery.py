"""add scheduled reports, artifact retention, and delivery records

Revision ID: 20260826_0008
Revises: 20260825_0007
Create Date: 2026-08-26 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260826_0008"
down_revision = "20260825_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # Deliberately no foreign key: artifacts.backend is switchable
        # (in_memory or postgres, see Settings.artifact_backend), so an
        # artifact this row names may not exist in this table at all.
        # DeliveryService enforces the reference at the application layer,
        # the same way saved_report_executions correlates to artifacts by
        # run_id rather than a foreign key.
        sa.Column("artifact_id", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        # A URL or an address, never a secret itself -- what an operator
        # explicitly configured as a destination, not credential material.
        sa.Column("destination", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        # Sanitized before it ever reaches this column -- see app.delivery.providers.
        sa.Column("provider_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_deliveries_artifact_created_at", "deliveries", ["artifact_id", "created_at"])
    op.create_index("ix_deliveries_status", "deliveries", ["status"])

    op.create_table(
        "scheduled_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("saved_report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("saved_reports.id", ondelete="RESTRICT"), nullable=False),
        # Denormalised from the saved report at creation time, the same way
        # saved_reports itself denormalises seed_narrative -- isolation stays
        # enforceable at this table's own query layer without a join.
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("schedule_kind", sa.String(length=16), nullable=False),
        sa.Column("schedule_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("formats", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("delivery_channel", sa.String(length=16), nullable=True),
        sa.Column("delivery_destination", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_result", sa.String(length=16), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        # Set by a worker claiming this row to run it; cleared when the run
        # finishes. A claim older than the worker's staleness cutoff is treated
        # as abandoned (a crashed worker) and becomes claimable again.
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scheduled_reports_due", "scheduled_reports", ["enabled", "next_run_at"])
    op.create_index("ix_scheduled_reports_workspace", "scheduled_reports", ["workspace_id"])
    op.create_index("ix_scheduled_reports_saved_report", "scheduled_reports", ["saved_report_id"])

    with op.batch_alter_table("saved_report_executions") as batch:
        batch.add_column(sa.Column(
            "scheduled_report_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scheduled_reports.id", ondelete="SET NULL"), nullable=True,
        ))
        batch.add_column(sa.Column("error_category", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("usage_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        batch.add_column(sa.Column("artifact_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_index(
        "ix_saved_report_executions_scheduled_report", "saved_report_executions", ["scheduled_report_id"],
    )

    with op.batch_alter_table("artifacts") as batch:
        batch.add_column(sa.Column("retention_policy", sa.String(length=16), nullable=False, server_default="standard"))
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("deletion_claimed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("deletion_attempts", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("deletion_error", sa.Text(), nullable=True))
    op.create_index(
        "ix_artifacts_retention", "artifacts", ["status", "retention_policy", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_artifacts_retention", table_name="artifacts")
    with op.batch_alter_table("artifacts") as batch:
        batch.drop_column("deletion_error")
        batch.drop_column("deletion_attempts")
        batch.drop_column("deletion_claimed_at")
        batch.drop_column("deleted_at")
        batch.drop_column("retention_policy")

    op.drop_index("ix_saved_report_executions_scheduled_report", table_name="saved_report_executions")
    with op.batch_alter_table("saved_report_executions") as batch:
        batch.drop_column("artifact_ids")
        batch.drop_column("usage_metadata")
        batch.drop_column("retry_count")
        batch.drop_column("error_category")
        batch.drop_column("scheduled_report_id")

    op.drop_index("ix_scheduled_reports_saved_report", table_name="scheduled_reports")
    op.drop_index("ix_scheduled_reports_workspace", table_name="scheduled_reports")
    op.drop_index("ix_scheduled_reports_due", table_name="scheduled_reports")
    op.drop_table("scheduled_reports")

    op.drop_index("ix_deliveries_status", table_name="deliveries")
    op.drop_index("ix_deliveries_artifact_created_at", table_name="deliveries")
    op.drop_table("deliveries")
