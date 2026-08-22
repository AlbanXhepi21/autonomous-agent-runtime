"""Tests for controlled task summarization without provider API calls."""

import logging
from typing import Sequence

import pytest

from app.contracts.actions import AgentAction
from app.runtime.runner import AgentRunner
from app.runtime.state import Observation, TaskSummary
from app.runtime.summarization import SummaryPolicy, TaskSummarizer
from app.core.limits import RuntimeLimits
from app.llm.contracts import LLMClient
from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry
from tests.support import ScriptedLLM, make_runner as build_runner


class FakeSummarizer(TaskSummarizer):
    """A deterministic summary implementation used only by tests."""

    def __init__(self) -> None:
        self.calls: list[list[int]] = []

    async def summarize(
        self, current_summary: TaskSummary, observations: Sequence[Observation]
    ) -> TaskSummary:
        sequences = [observation.sequence for observation in observations]
        self.calls.append(sequences)
        return current_summary.model_copy(
            update={
                "goal": "incorrect goal from summarizer",
                "progress": [*current_summary.progress, f"covered {sequences}"],
            }
        )


class FailingSummarizer(TaskSummarizer):
    async def summarize(
        self, current_summary: TaskSummary, observations: Sequence[Observation]
    ) -> TaskSummary:
        raise RuntimeError("summary provider unavailable")


def make_runner(
    llm: LLMClient, summarizer: TaskSummarizer, policy: SummaryPolicy
) -> AgentRunner:
    tools = ToolRegistry()
    tools.register(CalculatorTool())
    return build_runner(
        llm,
        tools,
        limits=RuntimeLimits(max_iterations=10),
        task_summarizer=summarizer,
        summary_policy=policy,
    )


def tool_action(number: int) -> AgentAction:
    return AgentAction(
        action_type="use_tool",
        reasoning_summary="Calculate the next result.",
        tool_name="calculator",
        tool_arguments={"expression": f"{number} + 1"},
    )


@pytest.mark.asyncio
async def test_summary_triggers_only_when_history_exceeds_configured_threshold() -> None:
    summarizer = FakeSummarizer()
    llm = ScriptedLLM([tool_action(1), tool_action(2), tool_action(3), tool_action(4), tool_action(5), AgentAction(action_type="finish", reasoning_summary="Done.", final_answer="Done.")])

    state = await make_runner(llm, summarizer, SummaryPolicy(trigger_observations=3, recent_observations=2)).run("Preserve this goal")

    assert summarizer.calls == [[1], [2], [3]]
    assert state.task_summary is not None
    assert state.task_summary.goal == "Preserve this goal"
    assert state.task_summary.last_updated_iteration == 5
    assert state.task_summary.summarized_observation_count == 3
    assert len(state.observations) == 5


@pytest.mark.asyncio
async def test_context_has_no_summary_before_trigger() -> None:
    summarizer = FakeSummarizer()
    llm = ScriptedLLM([tool_action(1), tool_action(2), AgentAction(action_type="finish", reasoning_summary="Done.", final_answer="Done.")])

    state = await make_runner(llm, summarizer, SummaryPolicy(trigger_observations=3, recent_observations=2)).run("Short task")

    assert summarizer.calls == []
    assert state.task_summary is None
    assert llm.contexts[2]["task_summary"] is None
    assert [item["sequence"] for item in llm.contexts[2]["recent_observations"]] == [1, 2]


@pytest.mark.asyncio
async def test_summary_context_retains_recent_observations_and_old_history() -> None:
    summarizer = FakeSummarizer()
    llm = ScriptedLLM([tool_action(1), tool_action(2), tool_action(3), tool_action(4), tool_action(5), AgentAction(action_type="finish", reasoning_summary="Done.", final_answer="Done.")])

    await make_runner(llm, summarizer, SummaryPolicy(trigger_observations=3, recent_observations=2)).run("Long task")

    final_context = llm.contexts[-1]
    assert final_context["task_summary"]["progress"] == ["covered [1]", "covered [2]", "covered [3]"]
    assert [item["sequence"] for item in final_context["recent_observations"]] == [4, 5]
    assert final_context["goal"] == "Long task"


@pytest.mark.asyncio
async def test_summarizer_failure_keeps_history_available_and_does_not_stop_run(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)
    llm = ScriptedLLM([tool_action(1), tool_action(2), tool_action(3), AgentAction(action_type="finish", reasoning_summary="Done.", final_answer="Done.")])

    state = await make_runner(llm, FailingSummarizer(), SummaryPolicy(trigger_observations=3, recent_observations=2)).run("Fallback safely")

    assert state.completed
    assert state.task_summary is None
    assert [item["sequence"] for item in llm.contexts[-1]["recent_observations"]] == [1, 2, 3]
    assert any(record.getMessage() == "task_summary_failed" for record in caplog.records)
