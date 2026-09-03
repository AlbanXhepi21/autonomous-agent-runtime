"""Cross-tenant repository isolation, against a real database.

Two real workspace rows (Tenant A, Tenant B) are minted for the duration of
this module. For every tenant-owned repository this suite creates a resource
under Tenant B and then proves Tenant A's own store, called with Tenant B's
real (not fabricated) identifier, returns nothing -- the same "direct UUID
substitution" attack the API-level isolation tests exercise over HTTP, here
proven one layer down, directly against the repository methods themselves.

A row from another workspace must be indistinguishable from a row that does
not exist at all: never a 403, always the same "not found" a caller gets for
a made-up id.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pytest_asyncio import fixture
from sqlalchemy import delete, select

pytest.importorskip("sqlalchemy")

from app.artifacts.files import WorkspaceArtifactFiles
from app.artifacts.postgres import PostgresArtifactStore
from app.conversations.store import PostgresConversationStore
from app.db.records import (
    AgentRunRecord,
    ArtifactRecord,
    ConversationRecord,
    DeliveryRecord,
    MemoryRecord,
    MessageRecord,
    WorkspaceRecord,
)
from app.db.session import Database
from app.delivery.store import PostgresDeliveryStore
from app.environment.workspace import Workspace
from app.memory.postgres import PostgresMemoryStore
from app.memory.records import Memory, MemoryType

pytestmark = pytest.mark.postgres

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


async def _insert_workspace(database: Database, workspace_id, slug: str) -> None:
    now = datetime.now(UTC)
    async with database.session() as session, session.begin():
        session.add(WorkspaceRecord(
            id=workspace_id, name=f"Isolation Test {slug}", slug=slug, is_active=True,
            default_timezone="UTC", default_locale="en-US", default_currency="USD",
            created_at=now, updated_at=now,
        ))


async def _purge(database: Database, workspace_ids: list) -> None:
    async with database.session() as session, session.begin():
        conversation_ids = select(ConversationRecord.id).where(ConversationRecord.workspace_id.in_(workspace_ids))
        await session.execute(delete(AgentRunRecord).where(AgentRunRecord.conversation_id.in_(conversation_ids)))
        await session.execute(delete(MessageRecord).where(MessageRecord.conversation_id.in_(conversation_ids)))
        await session.execute(delete(ConversationRecord).where(ConversationRecord.workspace_id.in_(workspace_ids)))
        await session.execute(delete(MemoryRecord).where(MemoryRecord.workspace_id.in_(workspace_ids)))
        await session.execute(delete(ArtifactRecord).where(ArtifactRecord.workspace_id.in_(workspace_ids)))
        await session.execute(delete(DeliveryRecord).where(DeliveryRecord.workspace_id.in_(workspace_ids)))
        await session.execute(delete(WorkspaceRecord).where(WorkspaceRecord.id.in_(workspace_ids)))


@fixture
async def tenants(tmp_path):
    """Two real, isolated workspace rows: Tenant A and Tenant B."""

    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    database = Database(TEST_DATABASE_URL)
    workspace_a, workspace_b = uuid4(), uuid4()
    await _insert_workspace(database, workspace_a, f"isolation-a-{workspace_a}")
    await _insert_workspace(database, workspace_b, f"isolation-b-{workspace_b}")
    try:
        yield database, workspace_a, workspace_b, Workspace(tmp_path)
    finally:
        await _purge(database, [workspace_a, workspace_b])
        await database.dispose()


@pytest.mark.asyncio
async def test_a_conversation_from_another_workspace_is_invisible(tenants) -> None:
    database, workspace_a, workspace_b, _workspace = tenants
    store = PostgresConversationStore(database)

    theirs = await store.create_conversation(workspace_id=workspace_b, title="Tenant B's conversation")

    assert await store.get_conversation(workspace_id=workspace_a, conversation_id=theirs.id) is None
    listed, total = await store.list_conversations(workspace_id=workspace_a, limit=50, offset=0)
    assert theirs.id not in {item.id for item in listed}
    assert await store.update_title(workspace_id=workspace_a, conversation_id=theirs.id, title="Stolen") is None
    assert await store.delete_conversation(workspace_id=workspace_a, conversation_id=theirs.id) is False
    # The row survives the refused delete, proven by Tenant B still seeing it.
    assert await store.get_conversation(workspace_id=workspace_b, conversation_id=theirs.id) is not None


@pytest.mark.asyncio
async def test_messages_and_runs_from_another_workspace_are_invisible(tenants) -> None:
    database, workspace_a, workspace_b, _workspace = tenants
    store = PostgresConversationStore(database)

    _conversation, _message, run = await store.create_run(
        workspace_id=workspace_b, conversation_id=None, message="Investigate Tenant B's refunds",
        run_id=f"isolation-test-{uuid4()}",
    )

    # A direct run_id substitution: Tenant A asks for a run id it never minted.
    assert await store.get_run(workspace_id=workspace_a, run_id=run.id) is None
    assert await store.get_assistant_message_for_run(workspace_id=workspace_a, run_id=run.id) is None
    messages, total = await store.list_messages(
        workspace_id=workspace_a, conversation_id=_conversation.id, limit=50, offset=0,
    )
    assert messages == [] and total == 0
    assert await store.list_runs(workspace_id=workspace_a, conversation_id=_conversation.id) == []
    # Tenant A's start_run silently no-ops against a run it does not own,
    # rather than mutating a row it was never given access to.
    await store.start_run(workspace_id=workspace_a, run_id=run.id, started_at=datetime.now(UTC))
    untouched = await store.get_run(workspace_id=workspace_b, run_id=run.id)
    assert untouched is not None and untouched.started_at is None


@pytest.mark.asyncio
async def test_a_memory_from_another_workspace_is_invisible(tenants) -> None:
    database, workspace_a, workspace_b, _workspace = tenants
    store = PostgresMemoryStore(database)

    theirs = await store.create(Memory(
        workspace_id=workspace_b, memory_type=MemoryType.LONG_TERM, content="Tenant B's billing secret.",
    ))

    assert await store.get(workspace_id=workspace_a, memory_id=theirs.id) is None
    assert await store.list_memories(workspace_id=workspace_a, memory_type=MemoryType.LONG_TERM) == []
    assert await store.delete(workspace_id=workspace_a, memory_id=theirs.id) is False
    # The row survives the refused delete.
    assert await store.get(workspace_id=workspace_b, memory_id=theirs.id) is not None


@pytest.mark.asyncio
async def test_an_artifact_from_another_workspace_is_invisible(tenants) -> None:
    database, workspace_a, workspace_b, workspace = tenants
    (workspace.root / "secret.pdf").write_text("Tenant B's report.")
    files = WorkspaceArtifactFiles(workspace, max_artifact_bytes=10_485_760)
    store = PostgresArtifactStore(files, database)

    theirs = await store.register(workspace_id=workspace_b, run_id="isolation-run", source_path="secret.pdf")

    assert await store.get(workspace_id=workspace_a, artifact_id=theirs.id) is None
    assert await store.path_for(workspace_id=workspace_a, artifact_id=theirs.id) is None
    assert await store.list(workspace_id=workspace_a, run_id="isolation-run") == []
    # Tenant B, correctly scoped, still sees its own artifact.
    assert await store.get(workspace_id=workspace_b, artifact_id=theirs.id) is not None


@pytest.mark.asyncio
async def test_a_delivery_from_another_workspace_is_invisible(tenants) -> None:
    database, workspace_a, workspace_b, _workspace = tenants
    store = PostgresDeliveryStore(database)

    theirs = await store.create(
        workspace_id=workspace_b, artifact_id="isolation-artifact", channel="link", destination="https://example.com",
    )

    assert await store.get(workspace_id=workspace_a, delivery_id=theirs.id) is None
    assert await store.list(workspace_id=workspace_a, artifact_id="isolation-artifact") == []
    with pytest.raises(Exception):
        await store.record_attempt(
            workspace_id=workspace_a, delivery_id=theirs.id, status="sent",
            provider_metadata={}, failure_reason=None,
        )
