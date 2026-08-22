"""Tests for model-selected, registry-validated delegation requests."""

import json
import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.runtime.context import ContextBuilder
from app.runtime.delegation import DelegationObservation, DelegationRequest
from app.contracts.actions import AgentAction
from app.runtime.registry import AgentRegistry
from app.runtime.runner import AgentRunner
from app.runtime.state import AgentState
from app.api.routes.agent import run_agent
from app.api.schemas.agent import AgentRunRequest
from app.core.limits import RuntimeLimits
from app.environment import CommandExecutor, PythonExecutor, Workspace
from app.environment.repository import Repository
from app.artifacts.store import WorkspaceArtifactStore
from app.llm.contracts import LLMClient
from app.skills.registry import SkillRegistry
from app.tools.calculator import CalculatorTool
from app.tools.commands import RunCommandTool
from app.tools.filesystem import ListFilesTool, ReadFileTool, WriteFileTool
from app.tools.python_exec import PythonExecTool
from app.tools.repository import GetChangedFilesTool, GetRepositoryTreeTool, GitInspectTool, SearchFilesTool
from app.tools.artifacts import RegisterArtifactTool
from app.tools.registry import ToolRegistry
from tests.support import ScriptedLLM, make_runner


def registries() -> tuple[ToolRegistry, SkillRegistry, AgentRegistry]:
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


def runner_for(llm: LLMClient) -> AgentRunner:
    tools, skills, agents = registries()
    return make_runner(
        llm, tools, skills, agent_registry=agents,
        limits=RuntimeLimits(max_iterations=3, max_recoverable_errors=3),
    )


def test_valid_delegation_action_parses_with_typed_fields() -> None:
    action = AgentAction.model_validate(
        {
            "action_type": "delegate",
            "reasoning_summary": "Specialist evidence would help.",
            "agent_name": "research",
            "objective": "Investigate model licensing restrictions.",
            "context": "The system will be used commercially.",
        }
    )

    assert action.action_type == "delegate"
    assert action.agent_name == "research"
    assert action.objective == "Investigate model licensing restrictions."
    request = DelegationRequest(
        parent_run_id="parent-1",
        parent_iteration=2,
        target_agent=action.agent_name,
        objective=action.objective,
        supplied_context=action.context,
    )
    assert request.parent_run_id == "parent-1"
    assert request.supplied_context == "The system will be used commercially."


@pytest.mark.parametrize(
    "payload",
    [
        {"agent_name": "research", "objective": "   "},
        {"agent_name": "", "objective": "Investigate licensing."},
        {"objective": "Investigate licensing."},
    ],
)
def test_empty_or_malformed_delegation_action_is_rejected(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        AgentAction.model_validate(
            {"action_type": "delegate", "reasoning_summary": "Delegate.", **payload}
        )


def test_specialist_metadata_is_compact_and_excludes_full_instructions() -> None:
    tools, skills, agents = registries()
    context = ContextBuilder(tools, skills, RuntimeLimits(), agent_registry=agents).build(
        AgentState(goal="Need an independent specialist")
    )

    metadata = context["available_specialist_agents"]
    assert [item["name"] for item in metadata] == ["data_analyst", "research", "software_engineer"]
    assert "Investigates external factual questions" in metadata[1]["description"]
    assert "Define the claim" not in json.dumps(context)


@pytest.mark.parametrize(
    "action",
    [
        AgentAction(action_type="use_tool", reasoning_summary="Calculate.", tool_name="calculator"),
        AgentAction(action_type="load_skill", reasoning_summary="Load guidance.", skill_name="research"),
        AgentAction(action_type="finish", reasoning_summary="Done.", final_answer="Done."),
    ],
)
def test_existing_action_choices_remain_valid(action: AgentAction) -> None:
    assert action.action_type in {"use_tool", "load_skill", "finish"}


@pytest.mark.asyncio
async def test_unknown_specialist_cannot_bypass_registry_validation(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)
    llm = ScriptedLLM(
        [
            AgentAction(
                action_type="delegate", reasoning_summary="Ask an unknown specialist.",
                agent_name="not_registered", objective="Do the task.",
            ),
            AgentAction(action_type="finish", reasoning_summary="Stop.", final_answer="No delegation."),
        ]
    )

    state = await runner_for(llm).run("Research this topic")

    assert state.completed
    assert state.delegation_requests == []
    assert isinstance(state.observations[0].content, DelegationObservation)
    assert state.observations[0].content.status == "invalid"
    event = next(record.event_fields for record in caplog.records if record.getMessage() == "delegation_invalid")
    assert event["target_agent"] == "not_registered"
    assert event["run_id"] == state.run_id


@pytest.mark.asyncio
async def test_runtime_safely_rejects_a_validation_bypassing_malformed_delegation() -> None:
    malformed = AgentAction.model_construct(
        action_type="delegate",
        reasoning_summary="Malformed provider payload.",
        agent_name="research",
        objective="   ",
        context=None,
    )
    llm = ScriptedLLM(
        [
            malformed,
            AgentAction(action_type="finish", reasoning_summary="Stop.", final_answer="Rejected."),
        ]
    )

    state = await runner_for(llm).run("Check a malformed request")

    # LLMDecision validates the action, so a payload that bypassed AgentAction's
    # own validation is rejected at the provider boundary and retried, rather
    # than reaching the delegation guard. Either way no delegation is fabricated;
    # the boundary check covers every action type, not only delegate.
    assert state.completed
    assert state.delegation_requests == []
    assert not any(
        isinstance(observation.content, DelegationObservation)
        for observation in state.observations
    )


@pytest.mark.asyncio
async def test_valid_delegation_is_requested_but_not_fabricated_or_executed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    llm = ScriptedLLM(
        [
            AgentAction(
                action_type="delegate", reasoning_summary="Independent research helps.",
                agent_name="research", objective="Check licensing restrictions.",
                context="Commercial use.",
            ),
            AgentAction(action_type="finish", reasoning_summary="Boundary reported.", final_answer="No child ran."),
        ]
    )

    state = await runner_for(llm).run("Check licensing")

    assert len(state.delegation_requests) == 1
    assert state.delegation_requests[0].target_agent == "research"
    outcome = state.observations[0].content
    assert isinstance(outcome, DelegationObservation)
    assert outcome.status == "unavailable"
    assert "child-agent execution is not available" in outcome.error
    assert not hasattr(outcome, "delegation_id")
    event = next(record.event_fields for record in caplog.records if record.getMessage() == "delegation_requested")
    assert event["run_id"] == state.run_id
    assert event["iteration"] == 1
    assert event["target_agent"] == "research"
    assert event["objective"] == "Check licensing restrictions."


@pytest.mark.asyncio
async def test_delegation_boundary_outcomes_are_not_reported_as_tool_outcomes() -> None:
    llm = ScriptedLLM(
        [
            AgentAction(
                action_type="delegate", reasoning_summary="Ask research.",
                agent_name="research", objective="Check licensing restrictions.",
            ),
            AgentAction(action_type="finish", reasoning_summary="Stop.", final_answer="No child ran."),
        ]
    )

    response = await run_agent(AgentRunRequest(goal="Check licensing"), runner_for(llm))

    assert response.tool_outcomes == []
    assert response.tools_used == []


@pytest.mark.asyncio
async def test_goal_keywords_do_not_trigger_automatic_specialist_routing() -> None:
    llm = ScriptedLLM(
        [AgentAction(action_type="finish", reasoning_summary="No specialist needed.", final_answer="Done.")]
    )

    state = await runner_for(llm).run("Research and analyze this technical architecture")

    assert state.delegation_requests == []
    assert llm.calls == 1
