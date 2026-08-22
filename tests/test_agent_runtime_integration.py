"""End-to-end runtime scenarios using deterministic provider-neutral fake LLMs."""

from typing import Any

import pytest

from app.agent.models import AgentAction
from app.agent.runner import AgentRunner
from app.agent.state import StopReason
from app.core.limits import RuntimeLimits
from app.llm.base import LLMClient
from app.tools.base import Tool
from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry
from tests.support import ScriptedLLM, make_runner as build_runner


class NeverFinishLLM(LLMClient):
    """Keep choosing distinct calls so the tool-call limit is exercised."""

    def __init__(self) -> None:
        self.calls = 0

    async def choose_action(
        self, *, system_prompt: str, context: dict[str, Any]
    ) -> AgentAction:
        self.calls += 1
        return AgentAction(
            action_type="use_tool",
            reasoning_summary="Continue calculating.",
            tool_name="calculator",
            tool_arguments={"expression": f"{self.calls} + 1"},
        )


class FailingTool(Tool):
    @property
    def name(self) -> str:
        return "failing"

    @property
    def description(self) -> str:
        return "Always fail for recovery testing."

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "additionalProperties": False}

    async def execute(self, **arguments: Any) -> str:
        raise RuntimeError("internal implementation detail")


def action(action_type: str, **payload: Any) -> AgentAction:
    return AgentAction(
        action_type=action_type, reasoning_summary="Take the next useful action.", **payload
    )


def make_runner(llm: LLMClient, limits: RuntimeLimits | None = None) -> AgentRunner:
    tools = ToolRegistry()
    tools.register(CalculatorTool())
    tools.register(FailingTool())
    return build_runner(llm, tools, limits=limits or RuntimeLimits())


@pytest.mark.asyncio
async def test_tool_then_finish_completes_with_a_tool_observation() -> None:
    runner = make_runner(
        ScriptedLLM(
            [
                action("use_tool", tool_name="calculator", tool_arguments={"expression": "2 + 2"}),
                action("finish", final_answer="4"),
            ]
        )
    )

    state = await runner.run("Calculate 2 + 2")

    assert state.completed
    assert state.stop_reason is StopReason.COMPLETED
    assert state.final_answer == "4"
    assert state.observations[0].content.output == "4"


@pytest.mark.asyncio
async def test_skill_then_tool_then_finish_preserves_progressive_disclosure() -> None:
    llm = ScriptedLLM(
        [
            action("load_skill", skill_name="data_analysis"),
            action("use_tool", tool_name="calculator", tool_arguments={"expression": "10 / 2"}),
            action("finish", final_answer="The result is 5."),
        ]
    )

    state = await make_runner(llm).run("Analyze a small number")

    assert state.completed
    assert "data_analysis" in state.loaded_skills
    assert state.observations[0].content.output == "5.0"
    assert "data_analysis" not in {skill["name"] for skill in llm.contexts[1]["available_skills"]}
    assert "data_analysis" in {skill["name"] for skill in llm.contexts[1]["loaded_skills"]}


@pytest.mark.asyncio
async def test_tool_failure_can_recover_with_a_different_tool() -> None:
    runner = make_runner(
        ScriptedLLM(
            [
                action("use_tool", tool_name="failing"),
                action("use_tool", tool_name="calculator", tool_arguments={"expression": "3 * 3"}),
                action("finish", final_answer="Recovered with 9."),
            ]
        )
    )

    state = await runner.run("Recover from a failed tool")

    assert state.completed
    assert state.recoverable_error_count == 1
    assert state.observations[0].content.error == "Tool execution failed."
    assert state.observations[1].content.output == "9"


@pytest.mark.asyncio
async def test_repeated_identical_action_is_observed_without_reexecution() -> None:
    repeated = action(
        "use_tool", tool_name="calculator", tool_arguments={"expression": "1 + 1"}
    )

    state = await make_runner(
        ScriptedLLM([repeated]),
        RuntimeLimits(max_iterations=4, max_consecutive_duplicate_actions=2),
    ).run("Repeat the same calculation")

    assert state.stop_reason is StopReason.MAX_ITERATIONS
    assert state.total_tool_calls == 2
    assert sum(
        observation.content.metadata.get("duplicate_action", False)
        for observation in state.observations
    ) == 2


@pytest.mark.asyncio
async def test_runaway_agent_stops_at_the_tool_call_limit() -> None:
    state = await make_runner(
        NeverFinishLLM(), RuntimeLimits(max_iterations=8, max_tool_calls=2)
    ).run("Keep working forever")

    assert state.stop_reason is StopReason.MAX_TOOL_CALLS
    assert not state.completed
    assert state.total_tool_calls == 2
    assert state.iteration_count == 3


@pytest.mark.asyncio
async def test_unknown_skill_becomes_a_recoverable_observation() -> None:
    runner = make_runner(
        ScriptedLLM(
            [
                action("load_skill", skill_name="missing"),
                action("finish", final_answer="That skill is unavailable."),
            ]
        )
    )

    state = await runner.run("Use an unavailable skill")

    assert state.completed
    assert state.recoverable_error_count == 1
    assert state.observations[0].source == "skill:missing"
    assert state.observations[0].content.error == "Unknown skill: missing."
