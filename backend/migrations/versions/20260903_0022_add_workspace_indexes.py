"""add workspace indexes

Revision ID: 20260903_0022
Revises: 20260903_0021
Create Date: 2026-09-03 00:00:06

Step 6 ("add tenant-scoped indexes"). Four brand-new composite indexes for
the tables that gained a direct ``workspace_id`` in this sequence, plus
three indexes recreated for ``data_sources``/``saved_reports``/
``scheduled_reports`` -- their original indexes lived on the plain string
``workspace_id`` column that 20260903_0020 dropped, which drops any index
defined on it along with it.
"""

from alembic import op

revision = "20260903_0022"
down_revision = "20260903_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_conversations_workspace_updated_at", "conversations", ["workspace_id", "updated_at"])
    op.create_index("ix_artifacts_workspace_created_at", "artifacts", ["workspace_id", "created_at"])
    op.create_index("ix_memories_workspace_type", "memories", ["workspace_id", "memory_type"])
    op.create_index("ix_deliveries_workspace_status", "deliveries", ["workspace_id", "status"])

    op.create_index("ix_data_sources_workspace", "data_sources", ["workspace_id"])
    op.create_index("ix_data_sources_workspace_status", "data_sources", ["workspace_id", "status"])
    op.create_index(
        "ix_saved_reports_workspace_status", "saved_reports", ["workspace_id", "status", "updated_at"],
    )
    op.create_index("ix_scheduled_reports_workspace", "scheduled_reports", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_scheduled_reports_workspace", table_name="scheduled_reports")
    op.drop_index("ix_saved_reports_workspace_status", table_name="saved_reports")
    op.drop_index("ix_data_sources_workspace_status", table_name="data_sources")
    op.drop_index("ix_data_sources_workspace", table_name="data_sources")

    op.drop_index("ix_deliveries_workspace_status", table_name="deliveries")
    op.drop_index("ix_memories_workspace_type", table_name="memories")
    op.drop_index("ix_artifacts_workspace_created_at", table_name="artifacts")
    op.drop_index("ix_conversations_workspace_updated_at", table_name="conversations")
