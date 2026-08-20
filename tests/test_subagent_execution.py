"""Integration tests for isolated, sequential specialist execution."""

import logging
from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agent.definition import AgentDefinition
from app.agent.delegation import (
    DelegationContext,
    DelegationMemory,
    DelegationRequest,
    MAX_DELEGATION_BACKGROUND_LENGTH,
    MAX_SUBAGENT_RESULT_LENGTH,
    SequentialSubagentExecutor,
    SubagentResult,
)
from app.agent.models import AgentAction
from app.agent.registry import AgentRegistry
from app.agent.runner import AgentRunner
from app.agent.state import AgentState, Observation
from app.core.limits import RuntimeLimits
from app.environment import CommandExecutor, PythonExecutor, Workspace
from app.environment.repository import Repository
from app.artifacts.store import WorkspaceArtifactStore
from app.llm.base import LLMClient
from app.skills.registry import SkillRegistry
from app.tools.calculator import CalculatorTool
from app.tools.commands import RunCommandTool
from app.tools.filesystem import ListFilesTool, ReadFileTool, WriteFileTool
from app.tools.python_exec import PythonExecTool
from app.tools.repository import GetChangedFilesTool, GetRepositoryTreeTool, GitInspectTool, SearchFilesTool
from app.tools.artifacts import RegisterArtifactTool
from app.tools.models import ToolResult
from app.tools.registry import ToolRegistry


class ScriptedLLM(LLMClient):
    def __init__(self, actions: list[AgentAction]) -> None:
        self._actions = actions
        self.calls = 0
        self.contexts: list[dict[str, object]] = []
        self.prompts: list[str] = []

    async def choose_action(self, *, system_prompt: str, context: dict[str, object]) -> AgentAction:
        self.prompts.append(system_prompt)
        self.contexts.append(context)
        action = self._actions[min(self.calls, len(self._actions) - 1)]
        self.calls += 1
        return action


def capabilities() -> tuple[ToolRegistry, SkillRegistry, AgentRegistry]:
    tools = ToolRegistry()
    tools.register(CalculatorTool())
    workspace = Workspace(Path.cwd())
    tools.register(ListFilesTool(workspace))
    tools.register(ReadFileTool(workspace))
    tools.register(WriteFileTool(workspace))
    tools.register(RunCommandTool(CommandExecutor(workspace)))
    tools.register(PythonExecTool(PythonExecutor(workspace)))
    repository = Repository(workspace)
    tools.register(GetRepositoryTreeTool(repository))
    tools.register(SearchFilesTool(repository))
    tools.register(GetChangedFilesTool(repository))
    tools.register(GitInspectTool(repository))
    tools.register(RegisterArtifactTool(WorkspaceArtifactStore(workspace)))
    skills = SkillRegistry()
    return tools, skills, AgentRegistry(tool_registry=tools, skill_registry=skills)


def make_parent(
    parent_llm: LLMClient,
    child_factory: Callable[[AgentDefinition], LLMClient],
) -> AgentRunner:
    tools, skills, agents = capabilities()
    limits = RuntimeLimits(max_iterations=5, max_tool_calls=4, max_recoverable_errors=3)
    return AgentRunner(
        parent_llm,
        tools,
        skills,
        limits=limits,
        agent_registry=agents,
        delegation_executor=SequentialSubagentExecutor(
            agent_registry=agents,
            tool_registry=tools,
            skill_registry=skills,
            llm_client_factory=child_factory,
            parent_limits=limits,
        ),
    )


def delegate(agent_name: str, objective: str, context: str | None = None) -> AgentAction:
    return AgentAction(
        action_type="delegate",
        reasoning_summary="A bounded independent specialist task would help.",
        agent_name=agent_name,
        objective=objective,
        context=context,
    )


@pytest.mark.asyncio
async def test_parent_child_parent_lifecycle_is_isolated_and_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    parent_llm = ScriptedLLM(
        [
            delegate("research", "Verify the license terms.", "Commercial deployment."),
            AgentAction(
                action_type="finish",
                reasoning_summary="Use the specialist outcome.",
                final_answer="Parent considered the child result.",
            ),
        ]
    )
    child_llm = ScriptedLLM(
        [
            AgentAction(
                action_type="finish",
                reasoning_summary="The delegated objective is complete.",
                final_answer="The license permits the stated use.",
            )
        ]
    )

    state = await make_parent(parent_llm, lambda _definition: child_llm).run("Assess licensing")

    assert state.completed
    assert state.final_answer == "Parent considered the child result."
    assert state.iteration_count == 2
    assert state.total_tool_calls == 0
    assert state.loaded_skills == {}
    result = state.observations[0].content
    assert isinstance(result, SubagentResult)
    assert result.success
    assert result.parent_run_id == state.run_id
    assert result.child_run_id and result.child_run_id != state.run_id
    assert result.agent_name == "research"
    assert result.answer == "The license permits the stated use."
    assert child_llm.contexts[0]["goal"] == "Verify the license terms."
    assert child_llm.contexts[0]["delegation_context"]["relevant_background"] == "Commercial deployment."
    assert child_llm.contexts[0]["available_tools"] == []
    assert [skill["name"] for skill in child_llm.contexts[0]["available_skills"]] == ["research"]
    assert "Define the claim" in child_llm.prompts[0]
    assert "Verify the license terms." in child_llm.prompts[0]
    assert "Commercial deployment." in child_llm.prompts[0]
    assert "software_engineer" not in child_llm.prompts[0]
    parent_observation = parent_llm.contexts[1]["recent_observations"][0]
    assert parent_observation["source"] == "subagent"
    assert parent_observation["agent"] == "research"
    assert parent_observation["objective"] == "Verify the license terms."
    assert parent_observation["result"] == "The license permits the stated use."
    events = [record.event_fields for record in caplog.records]
    started = next(item for item in events if item.get("agent") == "research" and "child_run_id" in item)
    finished = next(
        item for item in events if item.get("agent") == "research" and item.get("stop_reason") == "completed"
    )
    assert started["parent_run_id"] == state.run_id
    assert finished["child_run_id"] == result.child_run_id
    context_event = next(item for item in events if item.get("background_length") is not None)
    assert context_event["background_length"] == len("Commercial deployment.")
    assert context_event["memory_count"] == 0
    assert context_event["available_tool_count"] == 0
    assert context_event["available_skill_count"] == 1


@pytest.mark.asyncio
async def test_child_receives_only_agent_definition_capabilities() -> None:
    parent_llm = ScriptedLLM(
        [
            delegate("data_analyst", "Compute the requested metric."),
            AgentAction(action_type="finish", reasoning_summary="Done.", final_answer="Parent done."),
        ]
    )
    child_llm = ScriptedLLM(
        [
            AgentAction(
                action_type="use_tool",
                reasoning_summary="Calculate the metric.",
                tool_name="calculator",
                tool_arguments={"expression": "2 + 2"},
            ),
            AgentAction(action_type="finish", reasoning_summary="Use the calculation.", final_answer="4"),
        ]
    )

    state = await make_parent(parent_llm, lambda _definition: child_llm).run("Calculate")

    assert state.observations[0].content.success
    child_context = child_llm.contexts[0]
    assert [tool["name"] for tool in child_context["available_tools"]] == ["calculator"]
    assert [skill["name"] for skill in child_context["available_skills"]] == ["data_analysis", "executive_reporting"]


@pytest.mark.asyncio
async def test_child_cannot_access_ungranted_capability() -> None:
    parent_llm = ScriptedLLM(
        [
            delegate("research", "Investigate the claim."),
            AgentAction(action_type="finish", reasoning_summary="Done.", final_answer="Parent done."),
        ]
    )
    child_llm = ScriptedLLM(
        [
            AgentAction(
                action_type="use_tool",
                reasoning_summary="Try an ungranted capability.",
                tool_name="calculator",
                tool_arguments={"expression": "1 + 1"},
            ),
            AgentAction(action_type="finish", reasoning_summary="Report the limitation.", final_answer="No calculator access."),
        ]
    )

    state = await make_parent(parent_llm, lambda _definition: child_llm).run("Research")

    assert child_llm.contexts[0]["available_tools"] == []
    child_failure = child_llm.contexts[1]["recent_observations"][0]
    assert child_failure["error"] == "Unknown tool: calculator."
    result = state.observations[0].content
    assert isinstance(result, SubagentResult)
    assert result.success
    assert result.answer == "No calculator access."


@pytest.mark.asyncio
async def test_child_failure_is_a_parent_observation_not_a_parent_crash() -> None:
    parent_llm = ScriptedLLM(
        [
            delegate("research", "Investigate the claim."),
            AgentAction(action_type="finish", reasoning_summary="Report limitation.", final_answer="Limited."),
        ]
    )
    child_llm = ScriptedLLM(
        [
            AgentAction(
                action_type="use_tool",
                reasoning_summary="Try an unavailable tool.",
                tool_name="calculator",
                tool_arguments={"expression": "1 + 1"},
            )
        ]
    )

    state = await make_parent(parent_llm, lambda _definition: child_llm).run("Research")

    assert state.completed
    assert state.final_answer == "Limited."
    assert state.recoverable_error_count == 1
    result = state.observations[0].content
    assert isinstance(result, SubagentResult)
    assert not result.success
    assert result.stop_reason == "max_iterations"
    assert result.child_run_id != state.run_id


@pytest.mark.asyncio
async def test_unknown_specialist_is_rejected_before_child_execution() -> None:
    parent_llm = ScriptedLLM(
        [
            delegate("unknown", "Do work."),
            AgentAction(action_type="finish", reasoning_summary="Stop.", final_answer="No child."),
        ]
    )
    factories_called = 0

    def child_factory(_definition: AgentDefinition) -> LLMClient:
        nonlocal factories_called
        factories_called += 1
        return ScriptedLLM([])

    state = await make_parent(parent_llm, child_factory).run("Try an unknown specialist")

    assert factories_called == 0
    assert state.delegation_requests == []


@pytest.mark.asyncio
async def test_child_context_is_explicit_and_excludes_parent_state() -> None:
    parent_llm = ScriptedLLM(
        [
            AgentAction(
                action_type="delegate",
                reasoning_summary="Delegate bounded work.",
                agent_name="research",
                objective="Compare model licenses.",
                context="We are evaluating self-hosted models.",
                constraints="Focus only on licensing and commercial deployment.",
                expected_output="A concise comparison table.",
            ),
            AgentAction(action_type="finish", reasoning_summary="Done.", final_answer="Parent done."),
        ]
    )
    child_llm = ScriptedLLM(
        [AgentAction(action_type="finish", reasoning_summary="Done.", final_answer="Comparison.")]
    )
    parent_state = AgentState(
        goal="Parent goal with unrelated details",
        loaded_skills={"research": "PARENT-LOADED-SKILL-MUST-NOT-LEAK"},
        observations=[
            Observation(
                source="parent_tool",
                content=ToolResult(success=True, output="UNRELATED-PARENT-OBSERVATION"),
                iteration=1,
                sequence=1,
            )
        ],
        iteration_count=1,
    )

    state = await make_parent(parent_llm, lambda _definition: child_llm).run(
        parent_state.goal, state=parent_state
    )

    child_context = child_llm.contexts[0]
    delegation_context = child_context["delegation_context"]
    assert child_context["goal"] == "Compare model licenses."
    assert delegation_context == {
        "delegated_objective": "Compare model licenses.",
        "relevant_background": "We are evaluating self-hosted models.",
        "constraints": "Focus only on licensing and commercial deployment.",
        "expected_output": "A concise comparison table.",
        "relevant_memories": [],
    }
    rendered = str(child_context)
    assert "UNRELATED-PARENT-OBSERVATION" not in rendered
    assert "PARENT-LOADED-SKILL-MUST-NOT-LEAK" not in rendered
    assert child_context["loaded_skills"] == []
    assert state.loaded_skills == {"research": "PARENT-LOADED-SKILL-MUST-NOT-LEAK"}
    assert len(state.observations) == 2  # Existing parent observation plus bounded child result.


def test_delegation_context_enforces_its_size_boundaries() -> None:
    with pytest.raises(ValidationError):
        DelegationContext(
            objective="Bounded task",
            background="x" * (MAX_DELEGATION_BACKGROUND_LENGTH + 1),
        )


@pytest.mark.asyncio
async def test_child_receives_only_explicitly_selected_memory() -> None:
    tools, skills, agents = capabilities()
    child_llm = ScriptedLLM(
        [AgentAction(action_type="finish", reasoning_summary="Done.", final_answer="Used permitted memory.")]
    )
    executor = SequentialSubagentExecutor(
        agent_registry=agents,
        tool_registry=tools,
        skill_registry=skills,
        llm_client_factory=lambda _definition: child_llm,
        parent_limits=RuntimeLimits(),
    )
    request = DelegationRequest(
        parent_run_id="parent-run",
        parent_iteration=1,
        target_agent="research",
        objective="Use the permitted project fact.",
        context=DelegationContext(
            objective="Use the permitted project fact.",
            selected_memories=[
                DelegationMemory(reference="project-license", content="The project is commercial.")
            ],
        ),
    )

    result = await executor.execute(request)

    assert result.success
    child_context = child_llm.contexts[0]
    assert child_context["delegation_context"]["relevant_memories"] == [
        {"reference": "project-license", "content": "The project is commercial."}
    ]
    assert "UNRELATED-OTHER-SESSION-MEMORY" not in str(child_context)
    assert child_context["relevant_memories"] == []


@pytest.mark.asyncio
async def test_parent_receives_bounded_result_and_child_runs_do_not_share_state() -> None:
    parent_llm = ScriptedLLM(
        [
            delegate("research", "First isolated task."),
            delegate("research", "Second isolated task."),
            AgentAction(action_type="finish", reasoning_summary="Done.", final_answer="Parent done."),
        ]
    )
    first_child = ScriptedLLM(
        [
            AgentAction(action_type="load_skill", reasoning_summary="Load research.", skill_name="research"),
            AgentAction(
                action_type="finish",
                reasoning_summary="Done.",
                final_answer="A" * (MAX_SUBAGENT_RESULT_LENGTH + 20),
            ),
        ]
    )
    second_child = ScriptedLLM(
        [AgentAction(action_type="finish", reasoning_summary="Done.", final_answer="Fresh child.")]
    )
    children = iter([first_child, second_child])

    state = await make_parent(parent_llm, lambda _definition: next(children)).run("Two tasks")

    first_result = state.observations[0].content
    second_result = state.observations[1].content
    assert isinstance(first_result, SubagentResult)
    assert isinstance(second_result, SubagentResult)
    assert first_result.child_run_id != second_result.child_run_id
    assert len(first_result.answer or "") == MAX_SUBAGENT_RESULT_LENGTH
    assert (first_result.answer or "").endswith("...")
    assert second_child.contexts[0]["loaded_skills"] == []
    assert [skill["name"] for skill in second_child.contexts[0]["available_skills"]] == ["research"]
    assert "available_specialist_agents" not in second_child.contexts[0]
