"""Deterministic end-to-end memory scenarios; no provider calls are made."""

from typing import Sequence

import pytest

from app.contracts.actions import AgentAction
from app.agent.runner import AgentRunner
from app.agent.state import AgentState, Observation, TaskSummary
from app.agent.summarization import SummaryPolicy, TaskSummarizer
from app.core.limits import RuntimeLimits
from app.llm.contracts import LLMClient
from app.memory import (
    InMemoryMemoryStore, MemoryCandidate, MemoryCategory, MemoryManager, MemoryRetriever,
    MemoryType, MemoryWritingPipeline,
)
from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry
from tests.support import ScriptedLLM, make_runner


class DurableDecisionExtractor:
    async def extract(self, state: AgentState) -> Sequence[MemoryCandidate]:
        return [MemoryCandidate(
            content="The backend will use Redis cache-aside for read-heavy catalog responses.",
            memory_type=MemoryType.LONG_TERM,
            category=MemoryCategory.DECISION,
            reason="Explicit durable project decision.", source_run_id=state.run_id,
        )]


class FailingRetriever:
    async def retrieve(self, request: object) -> object:
        raise RuntimeError("memory store unavailable")


class FailingExtractor:
    async def extract(self, state: AgentState) -> Sequence[MemoryCandidate]:
        raise RuntimeError("candidate extraction unavailable")


class RecordingSummarizer(TaskSummarizer):
    async def summarize(
        self, current_summary: TaskSummary, observations: Sequence[Observation]
    ) -> TaskSummary:
        return current_summary.model_copy(
            update={"progress": [*current_summary.progress, f"covered {[item.sequence for item in observations]}"]}
        )


class FailingSummarizer(TaskSummarizer):
    async def summarize(
        self, current_summary: TaskSummary, observations: Sequence[Observation]
    ) -> TaskSummary:
        raise RuntimeError("summarizer unavailable")


def finish(answer: str = "Completed.") -> AgentAction:
    return AgentAction(action_type="finish", reasoning_summary="Finish the task.", final_answer=answer)


def calculation(number: int) -> AgentAction:
    return AgentAction(
        action_type="use_tool", reasoning_summary="Calculate deterministically.", tool_name="calculator",
        tool_arguments={"expression": f"{number} + 1"},
    )


def runner(
    llm: LLMClient, store: InMemoryMemoryStore, *, writer: MemoryWritingPipeline | None = None,
    retriever: object | None = None, summarizer: TaskSummarizer | None = None,
) -> AgentRunner:
    tools = ToolRegistry()
    tools.register(CalculatorTool())
    manager = MemoryManager(store)
    return make_runner(
        llm, tools, limits=RuntimeLimits(max_iterations=8), memory_manager=manager,
        memory_retriever=retriever if retriever is not None else MemoryRetriever(store),  # type: ignore[arg-type]
        memory_writer=writer, task_summarizer=summarizer,
        summary_policy=SummaryPolicy(trigger_observations=3, recent_observations=2),
    )


@pytest.mark.asyncio
async def test_scenarios_a_to_c_empty_relevant_and_irrelevant_memory_context() -> None:
    empty_store = InMemoryMemoryStore()
    empty_llm = ScriptedLLM([finish()])
    assert (await runner(empty_llm, empty_store).run("Plan a cache strategy")).completed  # A
    assert empty_llm.contexts[0]["relevant_memories"] == []

    store = InMemoryMemoryStore()
    manager = MemoryManager(store)
    await manager.add_long_term_memory("Project backend uses FastAPI and PostgreSQL.")
    await manager.add_long_term_memory("The office plants are watered every Friday.")
    llm = ScriptedLLM([finish()])
    await runner(llm, store).run("Recommend a caching strategy for this backend.")  # B/C

    assert [item["content"] for item in llm.contexts[0]["relevant_memories"]] == [
        "Project backend uses FastAPI and PostgreSQL."
    ]


@pytest.mark.asyncio
async def test_scenario_d_summary_keeps_old_history_compact_and_recent_history_detailed() -> None:
    store = InMemoryMemoryStore()
    llm = ScriptedLLM([calculation(1), calculation(2), calculation(3), calculation(4), finish()])
    await runner(llm, store, summarizer=RecordingSummarizer()).run("Calculate sequential values")

    context = llm.contexts[-1]
    assert context["task_summary"]["progress"] == ["covered [1]", "covered [2]"]
    assert [item["sequence"] for item in context["recent_observations"]] == [3, 4]


@pytest.mark.asyncio
async def test_scenarios_e_to_g_durable_write_transient_rejection_and_duplicate_prevention() -> None:
    store = InMemoryMemoryStore()
    manager = MemoryManager(store)
    writer = MemoryWritingPipeline(manager, extractor=DurableDecisionExtractor())
    await runner(ScriptedLLM([finish()]), store, writer=writer).run("Choose the cache design")  # E
    await runner(ScriptedLLM([finish()]), store, writer=writer).run("Repeat the cache decision")  # G
    assert len(await manager.get_memories(MemoryType.LONG_TERM)) == 1

    transient_writer = MemoryWritingPipeline(manager)
    await runner(
        ScriptedLLM([calculation(496), finish("calculator returned 497")]), store,
        writer=transient_writer,
    ).run("Calculate 496 + 1")  # F
    assert len(await manager.get_memories(MemoryType.LONG_TERM)) == 1


@pytest.mark.asyncio
async def test_scenarios_h_to_j_failures_leave_the_agent_and_context_usable() -> None:
    store = InMemoryMemoryStore()
    retrieval_llm = ScriptedLLM([finish()])
    assert (await runner(retrieval_llm, store, retriever=FailingRetriever()).run("Continue safely")).completed  # H
    assert retrieval_llm.contexts[0]["relevant_memories"] == []

    summary_llm = ScriptedLLM([calculation(1), calculation(2), calculation(3), finish()])
    summary_state = await runner(summary_llm, store, summarizer=FailingSummarizer()).run("Keep evidence")  # I
    assert summary_state.completed and summary_state.task_summary is None
    assert [item["sequence"] for item in summary_llm.contexts[-1]["recent_observations"]] == [1, 2, 3]

    failing_writer = MemoryWritingPipeline(MemoryManager(store), extractor=FailingExtractor())
    assert (await runner(ScriptedLLM([finish()]), store, writer=failing_writer).run("Still complete")).completed  # J
