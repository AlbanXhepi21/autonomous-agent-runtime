"""Tests for curated, policy-gated memory persistence after completed runs."""

import pytest

from app.memory import (
    InMemoryMemoryStore,
    MemoryCandidate,
    MemoryCategory,
    MemoryManager,
    MemoryType,
)
from app.memory.writing import MemoryWritingPipeline
from app.runtime.state import AgentState


class StaticExtractor:
    def __init__(self, candidates: list[MemoryCandidate]) -> None:
        self.candidates = candidates

    async def extract(self, state: AgentState) -> list[MemoryCandidate]:
        return self.candidates


class FailingExtractor:
    async def extract(self, state: AgentState) -> list[MemoryCandidate]:
        raise RuntimeError("extractor unavailable")


def candidate(
    content: str, *, memory_type: MemoryType = MemoryType.LONG_TERM,
    category: MemoryCategory = MemoryCategory.STABLE_FACT, metadata: dict | None = None,
) -> MemoryCandidate:
    return MemoryCandidate(
        content=content, memory_type=memory_type, category=category,
        reason="Useful durable context.", metadata=metadata or {}, source_run_id="run-1",
    )


async def capture(store: InMemoryMemoryStore, candidates: list[MemoryCandidate]) -> None:
    pipeline = MemoryWritingPipeline(MemoryManager(store), extractor=StaticExtractor(candidates))
    await pipeline.capture_completed_run(AgentState(goal="goal", run_id="run-1", completed=True))


@pytest.mark.asyncio
async def test_useful_candidate_is_accepted_as_long_term_memory() -> None:
    store = InMemoryMemoryStore()

    await capture(store, [candidate("The project uses FastAPI dependency injection for runtime services.")])

    memories = await MemoryManager(store).get_memories(MemoryType.LONG_TERM)
    assert [memory.content for memory in memories] == [
        "The project uses FastAPI dependency injection for runtime services."
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("content", [
    "Temporary calculation result: 2 + 2 = 4.",
    "Tool succeeded with status 200 and output received.",
    "Here is the answer to the task you asked me to complete today.",
])
async def test_transient_observations_and_tool_status_are_rejected(content: str) -> None:
    store = InMemoryMemoryStore()

    await capture(store, [candidate(content)])

    assert await MemoryManager(store).get_memories(MemoryType.LONG_TERM) == []


@pytest.mark.asyncio
async def test_duplicate_normalized_content_is_skipped() -> None:
    store = InMemoryMemoryStore()
    await capture(store, [candidate("The API requires an account identifier for billing.")])

    await capture(store, [candidate("The API requires an account identifier for billing!")])

    assert len(await MemoryManager(store).get_memories(MemoryType.LONG_TERM)) == 1


@pytest.mark.asyncio
async def test_episodic_candidate_is_created_with_source_run_id() -> None:
    store = InMemoryMemoryStore()

    await capture(store, [candidate(
        "Resolved the timeout by increasing the service connection pool limit.",
        memory_type=MemoryType.EPISODIC, category=MemoryCategory.RESOLVED_ISSUE,
    )])

    memories = await MemoryManager(store).get_memories(MemoryType.EPISODIC)
    assert memories[0].run_id == "run-1"


@pytest.mark.asyncio
async def test_proposed_candidate_cannot_bypass_policy_or_persist_private_reasoning() -> None:
    store = InMemoryMemoryStore()
    await capture(store, [
        candidate(
            "A durable sounding proposal that includes a private explanation.",
            metadata={"chain_of_thought": "private reasoning must never persist"},
        ),
        candidate("This contains private reasoning and must not become durable memory."),
    ])

    assert await MemoryManager(store).get_memories(MemoryType.LONG_TERM) == []


@pytest.mark.asyncio
async def test_extraction_failure_does_not_fail_completed_run() -> None:
    store = InMemoryMemoryStore()
    pipeline = MemoryWritingPipeline(MemoryManager(store), extractor=FailingExtractor())
    state = AgentState(goal="goal", run_id="run-1", completed=True)

    await pipeline.capture_completed_run(state)

    assert state.completed
    assert await MemoryManager(store).get_memories(MemoryType.LONG_TERM) == []


@pytest.mark.asyncio
async def test_candidate_reason_is_not_persisted() -> None:
    store = InMemoryMemoryStore()
    item = candidate("The system selects no more than five relevant historical memories.")
    item.reason = "This could be private chain-of-thought and is not durable context."

    await capture(store, [item])

    stored = (await MemoryManager(store).get_memories(MemoryType.LONG_TERM))[0]
    assert "reason" not in stored.metadata
    assert "chain-of-thought" not in stored.model_dump_json()


@pytest.mark.asyncio
async def test_candidate_cannot_claim_a_different_source_run() -> None:
    store = InMemoryMemoryStore()
    item = candidate("The project uses isolated session-scoped memory retrieval.")
    item.source_run_id = "other-run"

    await capture(store, [item])

    assert await MemoryManager(store).get_memories(MemoryType.LONG_TERM) == []
