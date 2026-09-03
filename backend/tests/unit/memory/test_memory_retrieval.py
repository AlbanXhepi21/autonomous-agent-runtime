"""Coverage for deterministic, bounded historical-memory selection."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.memory import InMemoryMemoryStore, Memory, MemoryRetrievalRequest, MemoryRetriever, MemoryType

WORKSPACE_ID = uuid.uuid4()


def memory(content: str, *, memory_type: MemoryType = MemoryType.LONG_TERM,
           session_id: str | None = None, age_days: int = 0, metadata: dict | None = None) -> Memory:
    return Memory(
        workspace_id=WORKSPACE_ID,
        memory_type=memory_type,
        content=content,
        session_id=session_id,
        metadata=metadata or {},
        created_at=datetime.now(timezone.utc) - timedelta(days=age_days),
    )


def request(**kwargs) -> MemoryRetrievalRequest:
    return MemoryRetrievalRequest(workspace_id=WORKSPACE_ID, **kwargs)


@pytest.mark.asyncio
async def test_retrieval_returns_no_memories_when_store_is_empty() -> None:
    result = await MemoryRetriever(InMemoryMemoryStore()).retrieve(request(query="billing API"))

    assert result.memories == []
    assert result.candidate_count == 0


@pytest.mark.asyncio
async def test_retrieval_selects_keyword_matches_and_excludes_irrelevant_memory() -> None:
    store = InMemoryMemoryStore()
    relevant = await store.create(memory("Billing API requires an account identifier."))
    await store.create(memory("The office plants are watered every Friday."))

    result = await MemoryRetriever(store).retrieve(request(query="billing account API"))

    assert [item.id for item in result.memories] == [relevant.id]
    assert result.candidate_count == 2


@pytest.mark.asyncio
async def test_retrieval_honors_limit_type_session_and_metadata_filters() -> None:
    store = InMemoryMemoryStore()
    episodic = await store.create(memory("Billing account failed", memory_type=MemoryType.EPISODIC, session_id="one", metadata={"project": "a"}))
    await store.create(memory("Billing account durable", session_id="one", metadata={"project": "a"}))
    await store.create(memory("Billing account elsewhere", memory_type=MemoryType.EPISODIC, session_id="two", metadata={"project": "a"}))

    result = await MemoryRetriever(store).retrieve(request(
        query="billing account", memory_types=(MemoryType.EPISODIC,), session_id="one",
        metadata_filters={"project": "a"}, limit=1,
    ))

    assert result.candidate_count == 1
    assert [item.id for item in result.memories] == [episodic.id]


@pytest.mark.asyncio
async def test_retrieval_isolates_session_memories_but_includes_global_memory() -> None:
    store = InMemoryMemoryStore()
    global_memory = await store.create(memory("Billing account architecture", session_id=None))
    own_memory = await store.create(memory("Billing account credentials", session_id="one"))
    await store.create(memory("Billing account secret from another session", session_id="two"))

    result = await MemoryRetriever(store).retrieve(
        request(query="billing account", session_id="one")
    )

    assert {item.id for item in result.memories} == {global_memory.id, own_memory.id}


@pytest.mark.asyncio
async def test_retrieval_uses_recency_as_a_deterministic_tie_breaker() -> None:
    store = InMemoryMemoryStore()
    old = await store.create(memory("Billing account note", age_days=5))
    recent = await store.create(memory("Billing account note", age_days=1))
    retriever = MemoryRetriever(store)

    first = await retriever.retrieve(request(query="billing account"))
    second = await retriever.retrieve(request(query="billing account"))

    assert [item.id for item in first.memories] == [recent.id, old.id]
    assert [item.id for item in second.memories] == [recent.id, old.id]


@pytest.mark.asyncio
async def test_retrieval_matches_requested_tags() -> None:
    store = InMemoryMemoryStore()
    tagged = await store.create(memory("A generic note", metadata={"tags": ["billing"]}))

    result = await MemoryRetriever(store).retrieve(request(query="unrelated", tags=("billing",)))

    assert [item.id for item in result.memories] == [tagged.id]
