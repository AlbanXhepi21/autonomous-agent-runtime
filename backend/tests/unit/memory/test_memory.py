"""Tests for memory models, storage isolation, and manager behavior."""

import asyncio
import logging

import pytest

from app.config import Settings
from app.memory import InMemoryMemoryStore, Memory, MemoryManager, MemoryType
from tests.support import logged_event


def test_postgres_backend_requires_a_database_url() -> None:
    with pytest.raises(ValueError, match="DATABASE_URL is required"):
        # Do not inherit a developer's local `.env` database URL in this missing-value test.
        Settings(memory_backend="postgres", database_url="")

    settings = Settings(
        memory_backend="postgres", database_url="postgresql+asyncpg://user:password@db/agent"
    )

    assert settings.memory_backend == "postgres"


@pytest.mark.asyncio
async def test_store_preserves_ids_and_returns_isolated_values() -> None:
    store = InMemoryMemoryStore()
    memory = Memory(memory_type=MemoryType.LONG_TERM, content="The API uses FastAPI.")

    created = await store.create(memory)
    created.metadata["changed"] = True
    retrieved = await store.get(memory.id)

    assert retrieved is not None
    assert retrieved.id == memory.id
    assert retrieved.metadata == {}


@pytest.mark.asyncio
async def test_store_filters_by_memory_type_run_and_session() -> None:
    store = InMemoryMemoryStore()
    await store.create(
        Memory(memory_type=MemoryType.WORKING, content="Current task", run_id="run-1", session_id="s-1")
    )
    await store.create(
        Memory(memory_type=MemoryType.WORKING, content="Other task", run_id="run-2", session_id="s-1")
    )
    await store.create(
        Memory(memory_type=MemoryType.EPISODIC, content="Past task", run_id="run-1", session_id="s-2")
    )

    memories = await store.list_memories(
        memory_type=MemoryType.WORKING, run_id="run-1", session_id="s-1"
    )

    assert [memory.content for memory in memories] == ["Current task"]


@pytest.mark.asyncio
async def test_store_is_safe_for_concurrent_creates() -> None:
    store = InMemoryMemoryStore()
    memories = [Memory(memory_type=MemoryType.WORKING, content=f"item {index}") for index in range(20)]

    await asyncio.gather(*(store.create(memory) for memory in memories))

    assert len(await store.list_memories()) == 20


@pytest.mark.asyncio
async def test_store_update_preserves_creation_time_and_refreshes_update_time() -> None:
    store = InMemoryMemoryStore()
    memory = await store.create(Memory(memory_type=MemoryType.EPISODIC, content="Initial"))

    updated = await store.update(memory.model_copy(update={"content": "Updated"}))

    assert updated is not None
    assert updated.content == "Updated"
    assert updated.created_at == memory.created_at
    assert updated.updated_at >= memory.updated_at


@pytest.mark.asyncio
async def test_manager_logs_updates_and_deletes(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    manager = MemoryManager(InMemoryMemoryStore())
    memory = await manager.add_episodic_memory("Initial")

    updated = await manager.update_memory(memory.model_copy(update={"content": "Revised"}))
    deleted = await manager.delete_memory(memory.id)

    assert updated is not None
    assert deleted
    assert {record.getMessage() for record in caplog.records} >= {
        "memory_created",
        "memory_updated",
        "memory_deleted",
    }


@pytest.mark.asyncio
async def test_manager_creates_typed_memories_and_clears_only_run_working_memory(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    manager = MemoryManager(InMemoryMemoryStore())
    working = await manager.add_working_memory("Investigate error", run_id="run-1")
    await manager.add_working_memory("Keep this", run_id="run-2")
    episodic = await manager.add_episodic_memory("Fixed timeout", run_id="run-1")
    durable = await manager.add_long_term_memory("Uses FastAPI")

    cleared = await manager.clear_working_memory("run-1")

    assert cleared == 1
    assert await manager.get_memories(MemoryType.WORKING, run_id="run-1") == []
    assert [memory.id for memory in await manager.get_memories(MemoryType.WORKING)] != [working.id]
    assert (await manager.get_memories(MemoryType.EPISODIC))[0].id == episodic.id
    assert (await manager.get_memories(MemoryType.LONG_TERM))[0].id == durable.id
    created = logged_event(caplog.records, "memory_created")
    assert created["run_id"] == "run-1"
    assert created["memory_id"] == str(working.id)
    assert created["memory_type"] is MemoryType.WORKING
    assert any(record.getMessage() == "working_memory_cleared" for record in caplog.records)
