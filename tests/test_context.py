"""Tests for the intentional model-facing agent context."""

import json

from app.agent.context import ContextBuilder
from app.agent.state import AgentState, Observation, TaskSummary
from app.core.limits import RuntimeLimits
from app.memory.models import Memory, MemoryType
from app.skills.registry import SkillRegistry
from app.tools.calculator import CalculatorTool
from app.tools.models import ToolResult
from app.tools.registry import ToolRegistry


def make_builder() -> ContextBuilder:
    tools = ToolRegistry()
    tools.register(CalculatorTool())
    return ContextBuilder(
        tools,
        SkillRegistry(),
        RuntimeLimits(max_iterations=5, max_tool_calls=7, max_recoverable_errors=2),
    )


def test_context_has_explicit_categories_and_preserves_goal() -> None:
    context = make_builder().build(AgentState(goal="Compare two libraries"))

    assert list(context) == [
        "goal",
        "task_summary",
        "working_memory",
        "relevant_memories",
        "runtime_status",
        "available_tools",
        "available_skills",
        "loaded_skills",
        "recent_observations",
    ]
    assert context["goal"] == "Compare two libraries"
    assert context["task_summary"] is None
    assert context["working_memory"] == []
    assert context["relevant_memories"] == []


def test_context_keeps_historical_memories_distinct_from_observations() -> None:
    memory = Memory(
        memory_type=MemoryType.LONG_TERM,
        content="The billing API needs an account ID.",
        metadata={"tags": ["billing"]},
    )

    context = make_builder().build(AgentState(goal="Use the billing API"), relevant_memories=[memory])

    assert context["relevant_memories"][0]["content"] == memory.content
    assert context["relevant_memories"][0]["memory_type"] is MemoryType.LONG_TERM
    assert context["recent_observations"] == []
    json.dumps(context)


def test_context_represents_compact_tool_and_unloaded_skill_metadata() -> None:
    context = make_builder().build(AgentState(goal="Use available capabilities"))

    calculator = context["available_tools"][0]
    assert calculator["name"] == "calculator"
    assert calculator["description"]
    assert calculator["arguments_schema"]["type"] == "object"
    research = next(skill for skill in context["available_skills"] if skill["name"] == "research")
    assert research["version"] == "1.0.0"
    assert "Define the claim" not in json.dumps(context)


def test_context_includes_loaded_instructions_but_not_as_available_metadata() -> None:
    registry = SkillRegistry()
    state = AgentState(goal="Research a claim")
    state.loaded_skills["research"] = registry.load_skill("research")

    context = ContextBuilder(ToolRegistry(), registry, RuntimeLimits()).build(state)

    assert context["loaded_skills"] == [
        {"name": "research", "instructions": state.loaded_skills["research"]}
    ]
    assert "research" not in {skill["name"] for skill in context["available_skills"]}


def test_context_flattens_recent_observations() -> None:
    state = AgentState(
        goal="Handle results",
        iteration_count=2,
        total_tool_calls=2,
        recoverable_error_count=1,
        observations=[
            Observation(
                source="calculator",
                content=ToolResult(success=True, output="4"),
                iteration=1,
                sequence=1,
            ),
            Observation(
                source="web_search",
                content=ToolResult(success=False, error="Tool execution failed."),
                iteration=2,
                sequence=2,
            ),
        ],
    )

    context = make_builder().build(state)

    assert context["recent_observations"] == [
        {"sequence": 1, "iteration": 1, "source": "calculator", "success": True, "output": "4", "error": None},
        {"sequence": 2, "iteration": 2, "source": "web_search", "success": False, "output": None, "error": "Tool execution failed."},
    ]
    assert "content" not in context["recent_observations"][0]


def test_context_uses_summary_for_old_history_and_preserves_recent_detail() -> None:
    state = AgentState(
        goal="Investigate a failure",
        observations=[
            Observation(source="tool", content=ToolResult(success=True, output=str(index)), iteration=index, sequence=index)
            for index in range(1, 7)
        ],
        task_summary=TaskSummary(
            goal="Investigate a failure",
            progress=["tool succeeded for observations 1 through 3"],
            last_updated_iteration=3,
            summarized_observation_count=3,
        ),
    )

    context = ContextBuilder(ToolRegistry(), SkillRegistry(), RuntimeLimits(), recent_observations=3).build(state)

    assert context["goal"] == "Investigate a failure"
    assert context["task_summary"]["progress"] == ["tool succeeded for observations 1 through 3"]
    assert [item["sequence"] for item in context["recent_observations"]] == [4, 5, 6]


def test_context_exposes_current_and_remaining_runtime_limits() -> None:
    state = AgentState(
        goal="Stay within limits",
        iteration_count=2,
        total_tool_calls=3,
        recoverable_error_count=1,
    )

    status = make_builder().build(state)["runtime_status"]

    assert status == {
        "current_iteration": 3,
        "maximum_iterations": 5,
        "remaining_iterations": 3,
        "tool_calls_used": 3,
        "tool_call_limit": 7,
        "remaining_tool_calls": 4,
        "recoverable_errors": 1,
        "recoverable_error_limit": 2,
        "remaining_recoverable_errors": 1,
    }


def test_context_module_is_independent_of_fastapi_and_openai_sdk() -> None:
    import app.agent.context as context_module

    source = open(context_module.__file__, encoding="utf-8").read()

    assert "fastapi" not in source.lower()
    assert "openai" not in source.lower()
