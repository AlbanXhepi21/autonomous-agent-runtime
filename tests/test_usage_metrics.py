"""V7.4 provider-neutral usage, cost, and latency aggregation coverage."""

import pytest

from app.agent.models import AgentAction
from app.agent.runner import AgentRunner
from app.core.limits import RuntimeLimits
from app.llm.base import LLMClient, LLMDecision, LLMUsage
from app.llm.pricing import ModelPricing, PricingRegistry, estimate_cost
from app.observability import InMemoryTraceStore, RunMetrics, RunTrace, TraceEvent, TraceEventType, TraceRecorder, aggregate_run_metrics
from app.skills.registry import SkillRegistry
from app.tools.registry import ToolRegistry


class UsageLLM(LLMClient):
    async def choose_action(self, *, system_prompt: str, context: dict[str, object]) -> AgentAction:
        return AgentAction(action_type="finish", reasoning_summary="", final_answer="Done")

    async def choose_decision(self, *, system_prompt: str, context: dict[str, object]) -> LLMDecision:
        return LLMDecision(action=await self.choose_action(system_prompt=system_prompt, context=context), model="test-model",
                           provider="test", usage=LLMUsage(input_tokens=1000, output_tokens=500,
                                                            cached_input_tokens=200, reasoning_tokens=30))


def test_usage_cost_calculation_and_unknown_pricing() -> None:
    usage = LLMUsage(input_tokens=1000, output_tokens=500, cached_input_tokens=200)
    pricing = ModelPricing(input_per_million=1.0, output_per_million=2.0, cached_input_per_million=0.5)
    assert estimate_cost(usage, pricing) == pytest.approx(0.0019)
    assert estimate_cost(usage, None) is None
    assert estimate_cost(LLMUsage(input_tokens=1), pricing) is None
    assert estimate_cost(usage, ModelPricing(1, 2)) is None


@pytest.mark.asyncio
async def test_run_usage_metrics_and_missing_usage() -> None:
    recorder = TraceRecorder(InMemoryTraceStore())
    runner = AgentRunner(UsageLLM(), ToolRegistry(), SkillRegistry(), limits=RuntimeLimits(), trace_recorder=recorder,
                         pricing_registry=PricingRegistry({"test-model": ModelPricing(1, 2, 0.5)}))
    state = await runner.run("Finish")
    metrics = recorder.get_trace(state.run_id).metrics  # type: ignore[union-attr]
    assert (metrics.llm_calls, metrics.input_tokens, metrics.output_tokens, metrics.cached_input_tokens) == (1, 1000, 500, 200)
    assert metrics.estimated_cost == pytest.approx(0.0019)
    assert metrics.llm_duration_ms >= 0 and metrics.total_duration_ms is not None

    plain = AgentRunner(UsageLLM(), ToolRegistry(), SkillRegistry(), limits=RuntimeLimits())
    # Base compatibility path is replaced with a decision here to prove unknown pricing stays null.
    state = await plain.run("Finish")
    assert plain._trace_recorder.get_trace(state.run_id).metrics.estimated_cost is None


def test_parent_child_cost_and_parallel_wall_clock_accounting() -> None:
    child_one = RunTrace(run_id="child-one", parent_run_id="parent", agent_name="one", agent_type="specialist", goal="one",
                         metrics=RunMetrics(iterations=6, llm_calls=1, total_tokens=10, estimated_cost=0.1, total_duration_ms=60))
    child_two = RunTrace(run_id="child-two", parent_run_id="parent", agent_name="two", agent_type="specialist", goal="two",
                         metrics=RunMetrics(iterations=3, llm_calls=1, total_tokens=20, estimated_cost=0.2, total_duration_ms=30))
    parent = RunTrace(run_id="parent", agent_name="primary", agent_type="primary", goal="parent",
                      events=[TraceEvent(run_id="parent", event_type=TraceEventType.PARALLEL_DELEGATION_FINISHED,
                                         metadata={"child_run_ids": ["child-one", "child-two"]})],
                      metrics=RunMetrics(iterations=4, llm_calls=1, total_tokens=5, estimated_cost=0.05, total_duration_ms=70))
    summary = aggregate_run_metrics(parent, {"child-one": child_one, "child-two": child_two}.get)
    assert (summary.total_iterations, summary.total_tokens, summary.total_estimated_cost) == (13, 35, pytest.approx(0.35))
    assert summary.wall_clock_duration_ms == 70
    assert summary.child_execution_duration_ms == 90


def test_trace_latency_aggregation_and_failed_run_metrics() -> None:
    store = InMemoryTraceStore(); recorder = TraceRecorder(store)
    recorder.start_run(run_id="failed", parent_run_id=None, agent_name="primary", agent_type="primary", goal="fail")
    recorder.record("failed", TraceEventType.LLM_REQUEST_FINISHED, duration_ms=12,
                    metadata={"input_tokens": 3, "output_tokens": 2, "estimated_cost": None})
    recorder.record("failed", TraceEventType.TOOL_FAILED, duration_ms=7, success=False)
    recorder.finish_run("failed", status="failed", stop_reason="fatal_error", metrics={"iterations": 1, "tool_calls": 1, "delegations": 0})
    metrics = store.get("failed").metrics  # type: ignore[union-attr]
    assert (metrics.llm_duration_ms, metrics.tool_duration_ms, metrics.total_tokens, metrics.estimated_cost) == (12, 7, 5, None)
