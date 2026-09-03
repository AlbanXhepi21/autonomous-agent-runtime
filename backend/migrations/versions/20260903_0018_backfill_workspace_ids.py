"""backfill workspace ids

Revision ID: 20260903_0018
Revises: 20260903_0017
Create Date: 2026-09-03 00:00:02

Step 2 ("backfill existing records"). Two different backfill rules, because
the two column groups started from different places:

- ``conversations``/``artifacts``/``memories``/``deliveries`` had *no* tenant
  concept before this migration at all -- every existing row goes to the
  single ``legacy`` workspace created in 20260903_0016. There is no signal
  in the data to do anything more specific, and guessing would be exactly
  the "silently assign ambiguous production data to the wrong user" this
  migration must not do.
- ``data_sources``/``saved_reports``/``scheduled_reports`` already carried a
  caller-supplied ``workspace_id`` *string* -- unauthenticated, but not
  meaningless: every route filtered its own reads by the same string. That
  nominal grouping is preserved rather than collapsed: the literal value
  ``"default"`` (the ``DEFAULT_WORKSPACE_ID`` every route actually used)
  maps to the same ``legacy`` workspace; every other distinct string gets
  its own new workspace, named ``Legacy: <original string>``.
"""

import re
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "20260903_0018"
down_revision = "20260903_0017"
branch_labels = None
depends_on = None

LEGACY_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
_DIRECT_TABLES = ("conversations", "artifacts", "memories", "deliveries")
_CONVERTED_TABLES = ("data_sources", "saved_reports", "scheduled_reports")

_SLUG_INVALID = re.compile(r"[^a-z0-9]+")


def _slugify(value: str, *, taken: set[str]) -> str:
    """Best-effort, collision-avoiding slug for an arbitrary legacy string."""

    base = _SLUG_INVALID.sub("-", value.strip().lower()).strip("-")[:56] or "legacy"
    candidate = f"legacy-{base}"
    suffix = 2
    while candidate in taken:
        candidate = f"legacy-{base}-{suffix}"[:64]
        suffix += 1
    taken.add(candidate)
    return candidate


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)

    for table in _DIRECT_TABLES:
        bind.execute(
            sa.text(f"UPDATE {table} SET workspace_id = CAST(:legacy AS uuid) WHERE workspace_id IS NULL")  # noqa: S608
            .bindparams(legacy=LEGACY_WORKSPACE_ID)
        )

    # Enumerate every distinct legacy string across all three converted tables.
    distinct_values: set[str] = set()
    for table in _CONVERTED_TABLES:
        rows = bind.execute(sa.text(f"SELECT DISTINCT workspace_id FROM {table}")).fetchall()  # noqa: S608
        distinct_values.update(row[0] for row in rows if row[0] is not None)

    taken_slugs = {row[0] for row in bind.execute(sa.text("SELECT slug FROM workspaces")).fetchall()}
    value_to_workspace_id: dict[str, str] = {}
    for value in sorted(distinct_values):
        if value.strip().lower() in {"", "default"}:
            value_to_workspace_id[value] = LEGACY_WORKSPACE_ID
            continue
        new_id = str(uuid.uuid4())
        slug = _slugify(value, taken=taken_slugs)
        bind.execute(
            sa.text(
                "INSERT INTO workspaces "
                "(id, name, slug, logo_ref, is_active, default_timezone, default_locale, default_currency, "
                "created_at, updated_at) "
                "VALUES (CAST(:id AS uuid), :name, :slug, NULL, TRUE, 'UTC', 'en-US', 'USD', :now, :now)"
            ).bindparams(id=new_id, name=f"Legacy: {value}"[:255], slug=slug, now=now)
        )
        value_to_workspace_id[value] = new_id

    for table in _CONVERTED_TABLES:
        for value, workspace_id in value_to_workspace_id.items():
            bind.execute(
                sa.text(f"UPDATE {table} SET workspace_id_new = CAST(:wid AS uuid) WHERE workspace_id = :value")  # noqa: S608
                .bindparams(wid=workspace_id, value=value)
            )


def downgrade() -> None:
    """Data-only migration; the columns themselves are reverted in 20260903_0017.

    Legacy workspace rows created here (everything except the fixed
    ``LEGACY_WORKSPACE_ID``) are intentionally left in place on downgrade --
    removing them could orphan a foreign key on a table this revision does
    not own the schema of.
    """
