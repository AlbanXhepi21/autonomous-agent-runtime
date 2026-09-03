"""add workspace foreign keys

Revision ID: 20260903_0021
Revises: 20260903_0020
Create Date: 2026-09-03 00:00:05

Step 5 ("add foreign keys"). ``ON DELETE RESTRICT`` on every one, matching
this codebase's existing convention that durable history is never silently
cascaded away (the same choice already made for
``agent_runs.conversation_id``, ``messages.conversation_id``,
``saved_report_executions.saved_report_id``, and every other "this row's
existence depends on its parent" foreign key in this schema).
"""

from alembic import op

revision = "20260903_0021"
down_revision = "20260903_0020"
branch_labels = None
depends_on = None

_TABLES = (
    "conversations", "artifacts", "memories", "deliveries",
    "data_sources", "saved_reports", "scheduled_reports",
)


def upgrade() -> None:
    for table in _TABLES:
        op.create_foreign_key(
            f"fk_{table}_workspace_id", table, "workspaces", ["workspace_id"], ["id"], ondelete="RESTRICT",
        )


def downgrade() -> None:
    for table in _TABLES:
        op.drop_constraint(f"fk_{table}_workspace_id", table, type_="foreignkey")
