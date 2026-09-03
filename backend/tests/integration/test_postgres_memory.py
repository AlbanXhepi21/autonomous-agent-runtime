"""Optional integration coverage for PostgreSQL memory-store semantics."""

import os
from uuid import UUID, uuid4

import pytest
from pytest_asyncio import fixture

pytest.importorskip("sqlalchemy")

from app.db.session import Database
from app.memory.postgres import PostgresMemoryStore
from app.memory.records import Memory, MemoryType

pytestmark = pytest.mark.postgres

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
#: The legacy workspace seeded by migration 20260903_0016 -- always present,
#: so single-tenant tests can use it as a valid FK target without minting rows.
WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000001")


@fixture
async def store() -> PostgresMemoryStore:
    """Connect to an already-migrated test database; never create its schema."""

    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    database = Database(TEST_DATABASE_URL)
    memory_store = PostgresMemoryStore(database)
    try:
        yield memory_store
    finally:
        await memory_store.close()


@pytest.mark.asyncio
async def test_postgres_store_matches_core_memory_store_semantics(
    store: PostgresMemoryStore,
) -> None:
    session_id = f"postgres-test-{uuid4()}"
    first = await store.create(
        Memory(
            workspace_id=WORKSPACE_ID,
            memory_type=MemoryType.WORKING,
            content="Current investigation",
            run_id="run-1",
            session_id=session_id,
            metadata={"source": "test"},
        )
    )
    second = await store.create(
        Memory(
            workspace_id=WORKSPACE_ID,
            memory_type=MemoryType.EPISODIC,
            content="Prior resolution",
            run_id="run-2",
            session_id=session_id,
        )
    )
    try:
        fetched = await store.get(workspace_id=WORKSPACE_ID, memory_id=first.id)
        assert fetched is not None and fetched.id == first.id
        assert [memory.id for memory in await store.list_memories(
            workspace_id=WORKSPACE_ID, memory_type=MemoryType.WORKING, run_id="run-1", session_id=session_id
        )] == [first.id]

        updated = await store.update(first.model_copy(update={"content": "Updated investigation"}))
        assert updated is not None
        assert updated.content == "Updated investigation"
        assert updated.created_at == first.created_at
        assert updated.updated_at >= first.updated_at
        assert await store.delete(workspace_id=WORKSPACE_ID, memory_id=first.id)
        assert await store.get(workspace_id=WORKSPACE_ID, memory_id=first.id) is None
    finally:
        await store.delete(workspace_id=WORKSPACE_ID, memory_id=first.id)
        await store.delete(workspace_id=WORKSPACE_ID, memory_id=second.id)
