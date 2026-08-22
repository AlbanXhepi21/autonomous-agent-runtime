"""Focused V7.1 trace coverage."""

import pytest

from app.agent.models import AgentAction
from app.agent.runner import AgentRunner
from app.core.limits import RuntimeLimits
from app.observability import InMemoryTraceStore, TraceEventType, TraceRecorder, TraceStatus
from app.skills.registry import SkillRegistry
from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry
from tests.support import ScriptedLLM


@pytest.mark.asyncio
async def test_trace_records_sanitized_run_llm_tool_and_skill_events() -> None:
    store = InMemoryTraceStore()
    recorder = TraceRecorder(store)
    tools = ToolRegistry()
    tools.register(CalculatorTool())
    runner = AgentRunner(
        ScriptedLLM([
            AgentAction(action_type="use_tool", reasoning_summary="private reasoning", tool_name="calculator",
                        tool_arguments={"expression": "1 + 1"}),
            AgentAction(action_type="finish", reasoning_summary="also private", final_answer="2"),
        ]),
        tools, SkillRegistry(), limits=RuntimeLimits(max_iterations=3), trace_recorder=recorder,
    )

    state = await runner.run("Calculate this with token=sk-secret-value-should-not-appear")
    trace = store.get(state.run_id)

    assert trace is not None and trace.status is TraceStatus.COMPLETED
    event_types = {event.event_type for event in trace.events}
    assert {TraceEventType.RUN_STARTED, TraceEventType.RUN_FINISHED,
            TraceEventType.LLM_REQUEST_STARTED, TraceEventType.LLM_REQUEST_FINISHED,
            TraceEventType.TOOL_STARTED, TraceEventType.TOOL_FINISHED,
            TraceEventType.SECURITY_POLICY_EVALUATED} <= event_types
    serialized = trace.model_dump_json()
    assert "private reasoning" not in serialized
    assert "sk-secret-value-should-not-appear" not in serialized


def test_in_memory_trace_store_has_bounded_retention() -> None:
    store = InMemoryTraceStore(max_traces=1)
    recorder = TraceRecorder(store)
    recorder.start_run(run_id="first", parent_run_id=None, agent_name="primary", agent_type="primary", goal="first")
    recorder.start_run(run_id="second", parent_run_id=None, agent_name="primary", agent_type="primary", goal="second")
    assert store.get("first") is None and store.get("second") is not None
