"""A finished answer may only cite evidence the run can account for."""

import logging

import pytest

from app.contracts.actions import AgentAction
from app.observability import InMemoryTraceStore, TraceEventType, TraceRecorder
from app.runtime.state import AgentState
from tests.support import ScriptedLLM, make_runner


def _finish(*citations: str) -> AgentAction:
    return AgentAction(action_type="finish", reasoning_summary="Evidence is sufficient.",
                       final_answer="Revenue fell because orders declined.",
                       citations=list(citations))


async def _run_with_queries(action: AgentAction, *queries: dict[str, object]) -> AgentState:
    recorder = TraceRecorder(InMemoryTraceStore())
    runner = make_runner(ScriptedLLM(action), trace_recorder=recorder)
    state = AgentState(goal="Why did revenue fall?")
    recorder.start_run(run_id=state.run_id, parent_run_id=None, agent_name="data_analyst",
                       agent_type="specialist", goal=state.goal)
    for query in queries:
        recorder.record(state.run_id, TraceEventType.DATABASE_QUERY_FINISHED, metadata=query)
    return await runner.run(state.goal, state=state)


@pytest.mark.asyncio
async def test_a_cited_query_becomes_a_stored_source() -> None:
    result = await _run_with_queries(
        _finish("query_001"),
        {"query_id": "query_001", "referenced_tables": ["orders"], "row_count": 8,
         "purpose": "Revenue by category"},
    )

    assert [source.id for source in result.answer_sources] == ["query_001"]
    assert result.answer_sources[0].label == "Revenue by category"


@pytest.mark.asyncio
async def test_a_reference_the_run_cannot_account_for_is_dropped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        result = await _run_with_queries(
            _finish("query_001", "query_007"),
            {"query_id": "query_001", "row_count": 8},
        )

    assert [source.id for source in result.answer_sources] == ["query_001"]
    assert result.final_answer == "Revenue fell because orders declined."
    assert any("answer_citation_unresolved" in record.getMessage() for record in caplog.records)


@pytest.mark.asyncio
async def test_an_answer_without_citations_still_completes() -> None:
    result = await _run_with_queries(_finish())

    assert result.completed is True
    assert result.answer_sources == []


def test_only_a_finish_action_may_carry_citations() -> None:
    with pytest.raises(ValueError, match="only finish actions may carry citations"):
        AgentAction(action_type="use_tool", reasoning_summary="Query the database.",
                    tool_name="query_database", citations=["query_001"])
