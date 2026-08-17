"""Starter tests for agent state and bounded execution."""

import logging

import pytest

from app.agent.models import AgentAction
from app.agent.policy import tool_action_fingerprint
from app.agent.runner import AgentRunner
from app.agent.state import AgentState, StopReason
from app.api.routes.agent import run_agent
from app.api.schemas.agent import AgentRunRequest
from app.core.limits import RuntimeLimits
from app.llm.base import LLMClient
from app.memory import InMemoryMemoryStore, MemoryManager, MemoryType
from app.skills.registry import SkillRegistry
from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry


class RepeatingToolLLM(LLMClient):
    """A fake client that never chooses to finish."""

    async def choose_action(self, *, system_prompt: str, context: dict[str, object]) -> AgentAction:
        return AgentAction(
            action_type="use_tool",
            reasoning_summary="Calculate the requested expression.",
            tool_name="calculator",
            tool_arguments={"expression": "1 + 1"},
        )


class RecoveringLLM(LLMClient):
    """Select an invalid tool, then finish after receiving the failure observation."""

    def __init__(self) -> None:
        self.contexts: list[dict[str, object]] = []

    async def choose_action(self, *, system_prompt: str, context: dict[str, object]) -> AgentAction:
        self.contexts.append(context)
        if len(self.contexts) == 1:
            return AgentAction(
                action_type="use_tool",
                reasoning_summary="Try a tool.",
                tool_name="missing",
            )
        return AgentAction(
            action_type="finish",
            reasoning_summary="The prior tool failed, so finish.",
            final_answer="Recovered from a tool failure.",
        )


class ScriptedLLM(LLMClient):
    """Return a fixed sequence of actions without making network calls."""

    def __init__(self, actions: list[AgentAction]) -> None:
        self._actions = actions
        self.calls = 0
        self.contexts: list[dict[str, object]] = []

    async def choose_action(self, *, system_prompt: str, context: dict[str, object]) -> AgentAction:
        self.contexts.append(context)
        action = self._actions[min(self.calls, len(self._actions) - 1)]
        self.calls += 1
        return action


class FailingLLM(LLMClient):
    """Raise a provider-like failure to exercise failed-run logging."""

    async def choose_action(self, *, system_prompt: str, context: dict[str, object]) -> AgentAction:
        raise RuntimeError("Provider unavailable")


def tool_action(name: str = "calculator", **arguments: object) -> AgentAction:
    return AgentAction(
        action_type="use_tool",
        reasoning_summary="Use a tool.",
        tool_name=name,
        tool_arguments=arguments,
    )


def make_runner(llm: LLMClient, limits: RuntimeLimits) -> AgentRunner:
    tools = ToolRegistry()
    tools.register(CalculatorTool())
    return AgentRunner(
        llm_client=llm,
        tool_registry=tools,
        skill_registry=SkillRegistry(),
        limits=limits,
    )


def logged_events(caplog: pytest.LogCaptureFixture, event: str) -> list[dict[str, object]]:
    """Return structured fields for the requested log event."""

    return [
        record.event_fields
        for record in caplog.records
        if record.getMessage() == event
    ]


def test_state_creation() -> None:
    state = AgentState(goal="Find an answer")

    assert state.goal == "Find an answer"
    assert state.iteration_count == 0
    assert state.observations == []
    assert not state.completed
    assert state.total_tool_calls == 0
    assert state.recoverable_error_count == 0
    assert state.stop_reason is None
    assert state.run_id


@pytest.mark.asyncio
async def test_runs_receive_unique_run_ids() -> None:
    runner = make_runner(
        ScriptedLLM(
            [
                AgentAction(
                    action_type="finish",
                    reasoning_summary="Done.",
                    final_answer="Done.",
                )
            ]
        ),
        RuntimeLimits(),
    )

    first = await runner.run("First")
    second = await runner.run("Second")

    assert first.run_id != second.run_id


@pytest.mark.asyncio
async def test_runner_uses_memory_manager_without_exposing_memory_to_llm_context() -> None:
    store = InMemoryMemoryStore()
    manager = MemoryManager(store)
    llm = ScriptedLLM(
        [AgentAction(action_type="finish", reasoning_summary="Done.", final_answer="Done.")]
    )
    tools = ToolRegistry()
    tools.register(CalculatorTool())
    runner = AgentRunner(llm, tools, SkillRegistry(), memory_manager=manager)

    state = await runner.run("Keep this run-local")

    assert state.completed
    assert await manager.get_memories(MemoryType.WORKING, run_id=state.run_id) == []
    assert "memories" not in llm.contexts[0]


@pytest.mark.asyncio
async def test_runner_stops_at_iteration_limit() -> None:
    tools = ToolRegistry()
    tools.register(CalculatorTool())
    runner = AgentRunner(
        llm_client=RepeatingToolLLM(),
        tool_registry=tools,
        skill_registry=SkillRegistry(),
        max_iterations=2,
    )

    state = await runner.run("Calculate one plus one")

    assert state.iteration_count == 2
    assert len(state.observations) == 2
    assert not state.completed
    assert state.stop_reason is StopReason.MAX_ITERATIONS
    assert state.final_answer == "Agent stopped after reaching the maximum iteration limit."


@pytest.mark.asyncio
async def test_runner_continues_after_recoverable_tool_failure() -> None:
    llm = RecoveringLLM()
    tools = ToolRegistry()
    tools.register(CalculatorTool())
    runner = AgentRunner(
        llm_client=llm,
        tool_registry=tools,
        skill_registry=SkillRegistry(),
        max_iterations=3,
    )

    state = await runner.run("Recover from an invalid tool request")

    assert state.completed
    assert state.final_answer == "Recovered from a tool failure."
    assert state.iteration_count == 2
    assert state.recoverable_error_count == 1
    assert state.stop_reason is StopReason.COMPLETED
    assert not state.observations[0].content.success
    assert llm.contexts[1]["observations"] == [
        {
            "sequence": 1,
            "iteration": 1,
            "source": "missing",
            "success": False,
            "output": None,
            "error": "Unknown tool: missing.",
        }
    ]


@pytest.mark.asyncio
async def test_runner_records_normal_completion() -> None:
    runner = make_runner(
        ScriptedLLM(
            [
                AgentAction(
                    action_type="finish",
                    reasoning_summary="The goal is complete.",
                    final_answer="Done.",
                )
            ]
        ),
        RuntimeLimits(),
    )

    state = await runner.run("Finish immediately")

    assert state.completed
    assert state.stop_reason is StopReason.COMPLETED
    assert state.iteration_count == 1
    assert state.final_answer == "Done."


@pytest.mark.asyncio
async def test_completion_logs_lifecycle_events(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    runner = make_runner(
        ScriptedLLM(
            [
                AgentAction(
                    action_type="finish",
                    reasoning_summary="Done.",
                    final_answer="Done.",
                )
            ]
        ),
        RuntimeLimits(),
    )

    state = await runner.run("Finish")

    started = logged_events(caplog, "agent_run_started")
    action = logged_events(caplog, "llm_action_selected")
    finished = logged_events(caplog, "agent_finished")
    assert started[0]["run_id"] == state.run_id
    assert action[0]["run_id"] == state.run_id
    assert action[0]["action"] == "finish"
    assert finished[0]["stop_reason"] is StopReason.COMPLETED
    assert finished[0]["duration_ms"] >= 0


@pytest.mark.asyncio
async def test_failed_run_is_logged_with_its_run_id(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR)
    runner = make_runner(FailingLLM(), RuntimeLimits())

    with pytest.raises(RuntimeError, match="Provider unavailable"):
        await runner.run("Fail")

    event = logged_events(caplog, "agent_run_failed")[0]
    assert event["error_type"] == "RuntimeError"
    assert event["run_id"]


@pytest.mark.asyncio
async def test_runner_enforces_maximum_tool_calls() -> None:
    runner = make_runner(
        ScriptedLLM([tool_action(expression="1 + 1"), tool_action(expression="2 + 2")]),
        RuntimeLimits(max_iterations=5, max_tool_calls=1),
    )

    state = await runner.run("Use tools")

    assert state.stop_reason is StopReason.MAX_TOOL_CALLS
    assert not state.completed
    assert state.total_tool_calls == 1
    assert len(state.observations) == 1
    assert state.iteration_count == 2


@pytest.mark.asyncio
async def test_runtime_limit_termination_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    runner = make_runner(
        ScriptedLLM([tool_action(expression="1 + 1"), tool_action(expression="2 + 2")]),
        RuntimeLimits(max_iterations=5, max_tool_calls=1),
    )

    state = await runner.run("Use tools")

    event = logged_events(caplog, "runtime_limit_reached")[0]
    assert event["run_id"] == state.run_id
    assert event["limit_type"] == "max_tool_calls"
    assert event["configured_limit"] == 1


@pytest.mark.asyncio
async def test_runner_enforces_maximum_recoverable_errors() -> None:
    runner = make_runner(
        ScriptedLLM([tool_action("missing", attempt=1), tool_action("missing", attempt=2)]),
        RuntimeLimits(max_iterations=5, max_recoverable_errors=2),
    )

    state = await runner.run("Try unavailable tools")

    assert state.stop_reason is StopReason.TOO_MANY_ERRORS
    assert not state.completed
    assert state.recoverable_error_count == 2
    assert state.total_tool_calls == 2
    assert state.iteration_count == 2


@pytest.mark.asyncio
async def test_duplicate_actions_are_observed_without_being_executed_again() -> None:
    runner = make_runner(
        ScriptedLLM([tool_action(expression="1 + 1")]),
        RuntimeLimits(max_iterations=4, max_consecutive_duplicate_actions=2),
    )

    state = await runner.run("Keep calculating")

    assert state.total_tool_calls == 2
    assert state.iteration_count == 4
    assert state.stop_reason is StopReason.MAX_ITERATIONS
    duplicate_observations = [
        observation
        for observation in state.observations
        if observation.content.metadata.get("duplicate_action")
    ]
    assert len(duplicate_observations) == 2
    assert "change approach" in (duplicate_observations[0].content.error or "")
    assert state.recoverable_error_count == 0


@pytest.mark.asyncio
async def test_duplicate_action_detection_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    runner = make_runner(
        ScriptedLLM([tool_action(expression="1 + 1")]),
        RuntimeLimits(max_iterations=3, max_consecutive_duplicate_actions=2),
    )

    state = await runner.run("Repeat")

    event = logged_events(caplog, "duplicate_action_detected")[0]
    assert event["run_id"] == state.run_id
    assert event["tool"] == "calculator"
    assert event["duplicate_count"] == 3


@pytest.mark.asyncio
async def test_skill_loading_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    runner = make_runner(
        ScriptedLLM(
            [
                AgentAction(
                    action_type="load_skill",
                    reasoning_summary="Use research guidance.",
                    skill_name="research",
                ),
                AgentAction(
                    action_type="finish",
                    reasoning_summary="Done.",
                    final_answer="Done.",
                ),
            ]
        ),
        RuntimeLimits(),
    )

    state = await runner.run("Research")

    event = logged_events(caplog, "skill_loaded")[0]
    assert event["run_id"] == state.run_id
    assert event["skill"] == "research"


def test_tool_action_fingerprint_ignores_argument_mapping_order() -> None:
    first = tool_action_fingerprint("web_search", {"query": "example", "limit": 3})
    second = tool_action_fingerprint("web_search", {"limit": 3, "query": "example"})

    assert first == second


@pytest.mark.asyncio
async def test_successful_tool_actions_do_not_increment_error_count() -> None:
    runner = make_runner(
        ScriptedLLM(
            [
                tool_action(expression="1 + 1"),
                AgentAction(
                    action_type="finish",
                    reasoning_summary="Result received.",
                    final_answer="2",
                ),
            ]
        ),
        RuntimeLimits(),
    )

    state = await runner.run("Calculate")

    assert state.completed
    assert state.recoverable_error_count == 0
    assert state.observations[0].content.success


@pytest.mark.asyncio
async def test_agent_response_includes_safe_execution_summary() -> None:
    runner = make_runner(
        ScriptedLLM(
            [
                tool_action("missing"),
                AgentAction(
                    action_type="finish",
                    reasoning_summary="Stop after the failure.",
                    final_answer="Tool unavailable.",
                ),
            ]
        ),
        RuntimeLimits(),
    )

    response = await run_agent(AgentRunRequest(goal="Use a missing tool"), runner)

    assert response.run_id
    assert response.tool_call_count == 1
    assert response.recoverable_error_count == 1
    assert response.tools_used == ["missing"]
    assert response.tool_outcomes[0].tool_name == "missing"
    assert not response.tool_outcomes[0].success
    assert response.tool_outcomes[0].error == "Unknown tool: missing."


@pytest.mark.asyncio
async def test_agent_response_does_not_report_skill_failures_as_tool_outcomes() -> None:
    runner = make_runner(
        ScriptedLLM(
            [
                AgentAction(
                    action_type="load_skill",
                    reasoning_summary="Try the requested skill.",
                    skill_name="missing",
                ),
                AgentAction(
                    action_type="finish",
                    reasoning_summary="The skill is unavailable.",
                    final_answer="Skill unavailable.",
                ),
            ]
        ),
        RuntimeLimits(),
    )

    response = await run_agent(AgentRunRequest(goal="Use a missing skill"), runner)

    assert response.recoverable_error_count == 1
    assert response.tools_used == []
    assert response.tool_outcomes == []
