"""Tests for explicit, bounded parallel specialist delegation."""

import asyncio
import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.specialists import AgentDefinition
from app.agent.delegation import (
    ParallelDelegationResult,
    ParallelSubagentExecutor,
    SequentialSubagentExecutor,
    SubagentResult,
)
from app.contracts.actions import AgentAction
from app.agent.registry import AgentRegistry
from app.agent.runner import AgentRunner
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
from tests.support import make_runner as build_runner


class ParentLLM(LLMClient):
    def __init__(self, actions: list[AgentAction]) -> None:
        self._actions = actions
        self.calls = 0
        self.contexts: list[dict[str, object]] = []

    async def choose_action(self, *, system_prompt: str, context: dict[str, object]) -> AgentAction:
        self.contexts.append(context)
        action = self._actions[min(self.calls, len(self._actions) - 1)]
        self.calls += 1
        return action


class ChildLLM(LLMClient):
    def __init__(
        self, answer: str, *, delay: float = 0, fail: bool = False,
        active: list[int] | None = None,
    ) -> None:
        self._answer = answer
        self._delay = delay
        self._fail = fail
        self._active = active
        self.contexts: list[dict[str, object]] = []

    async def choose_action(self, *, system_prompt: str, context: dict[str, object]) -> AgentAction:
        self.contexts.append(context)
        if self._active is not None:
            self._active[0] += 1
            self._active[1] = max(self._active[1], self._active[0])
        try:
            await asyncio.sleep(self._delay)
            if self._fail:
                raise RuntimeError("simulated child failure")
            return AgentAction(
                action_type="finish", reasoning_summary="Delegated task complete.", final_answer=self._answer
            )
        finally:
            if self._active is not None:
                self._active[0] -= 1


class ActionLLM(LLMClient):
    def __init__(self, actions: list[AgentAction]) -> None:
        self._actions = actions
        self.calls = 0
        self.contexts: list[dict[str, object]] = []

    async def choose_action(self, *, system_prompt: str, context: dict[str, object]) -> AgentAction:
        self.contexts.append(context)
        action = self._actions[min(self.calls, len(self._actions) - 1)]
        self.calls += 1
        return action


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


def parallel_action(*items: dict[str, str]) -> AgentAction:
    return AgentAction(
        action_type="delegate_parallel",
        reasoning_summary="These independent specialist tasks can run concurrently.",
        delegations=list(items),
    )


def test_parallel_action_requires_multiple_typed_delegations() -> None:
    with pytest.raises(ValidationError, match="at least two"):
        AgentAction(
            action_type="delegate_parallel",
            reasoning_summary="Not enough independent work.",
            delegations=[{"agent_name": "research", "objective": "Only one."}],
        )


@pytest.mark.asyncio
async def test_parent_can_finish_a_simple_tool_task_without_delegating() -> None:
    parent = ParentLLM(
        [
            AgentAction(
                action_type="use_tool", reasoning_summary="Calculate directly.",
                tool_name="calculator", tool_arguments={"expression": "2 + 2"},
            ),
            AgentAction(action_type="finish", reasoning_summary="Use calculation.", final_answer="4"),
        ]
    )

    state = await make_runner(parent, lambda _definition: ChildLLM("unused")).run("Calculate 2 + 2.")

    assert state.completed and state.final_answer == "4"
    assert state.delegation_requests == []
    assert state.successful_delegation_count == 0


def make_runner(
    parent: LLMClient,
    factory: callable,
    *,
    max_parallel: int = 3,
    max_delegations: int = 8,
    max_subagent_iterations: int = 6,
) -> AgentRunner:
    tools, skills, agents = registries()
    limits = RuntimeLimits(
        max_iterations=5,
        max_parallel_subagents=max_parallel,
        max_delegations_per_run=max_delegations,
        max_subagent_iterations=max_subagent_iterations,
    )
    sequential = SequentialSubagentExecutor(
        agent_registry=agents,
        tool_registry=tools,
        skill_registry=skills,
        llm_client_factory=factory,
        parent_limits=limits,
    )
    return build_runner(
        parent,
        tools,
        skills,
        limits=limits,
        agent_registry=agents,
        delegation_executor=sequential,
        parallel_delegation_executor=ParallelSubagentExecutor(
            sequential, max_parallel_subagents=max_parallel
        ),
    )


@pytest.mark.asyncio
async def test_two_independent_children_run_concurrently_and_parent_continues(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    active = [0, 0]
    research = ChildLLM("License evidence.", delay=0.03, active=active)
    analyst = ChildLLM("Cost analysis.", delay=0.03, active=active)
    parent = ParentLLM(
        [
            parallel_action(
                {"agent_name": "research", "objective": "Investigate licenses."},
                {"agent_name": "data_analyst", "objective": "Analyze costs."},
            ),
            AgentAction(action_type="finish", reasoning_summary="Use both outcomes.", final_answer="Combined."),
        ]
    )
    children = {"research": research, "data_analyst": analyst}

    state = await make_runner(parent, lambda definition: children[definition.name]).run("Compare options")

    assert state.completed and state.final_answer == "Combined."
    assert active == [0, 2]
    parallel = state.observations[0].content
    assert isinstance(parallel, ParallelDelegationResult)
    assert [result.agent_name for result in parallel.results] == ["research", "data_analyst"]
    assert all(result.success for result in parallel.results)
    assert len({result.child_run_id for result in parallel.results}) == 2
    assert research.contexts[0]["goal"] == "Investigate licenses."
    assert analyst.contexts[0]["goal"] == "Analyze costs."
    assert "Analyze costs." not in str(research.contexts[0])
    assert "Investigate licenses." not in str(analyst.contexts[0])
    observation = parent.contexts[1]["recent_observations"][0]
    assert observation["source"] == "parallel_subagents"
    assert [item["agent"] for item in observation["results"]] == ["research", "data_analyst"]
    events = [record.getMessage() for record in caplog.records]
    assert "parallel_delegation_started" in events
    assert "parallel_delegation_finished" in events


@pytest.mark.asyncio
async def test_partial_failure_preserves_successful_sibling_and_cleans_up_tasks(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)
    active = [0, 0]
    research = ChildLLM("Research result.", delay=0.02, active=active)
    broken = ChildLLM("", delay=0.01, fail=True, active=active)
    parent = ParentLLM(
        [
            parallel_action(
                {"agent_name": "research", "objective": "Research independently."},
                {"agent_name": "software_engineer", "objective": "Inspect architecture."},
            ),
            AgentAction(action_type="finish", reasoning_summary="Report partial outcome.", final_answer="Partial."),
        ]
    )
    children = {"research": research, "software_engineer": broken}

    state = await make_runner(parent, lambda definition: children[definition.name]).run("Parallel review")

    assert state.completed and state.final_answer == "Partial."
    assert active[0] == 0
    parallel = state.observations[0].content
    assert isinstance(parallel, ParallelDelegationResult)
    assert parallel.results[0].success and parallel.results[0].answer == "Research result."
    assert not parallel.results[1].success
    assert parallel.results[1].error == "Subagent execution failed."
    assert state.successful_delegation_count == 1
    assert state.failed_delegation_count == 1
    assert state.parallel_delegation_batch_count == 1
    assert len(state.child_run_ids) == 2
    assert any(record.getMessage() == "parallel_delegation_partial_failure" for record in caplog.records)


@pytest.mark.asyncio
async def test_runtime_rejects_batches_above_hard_concurrency_limit() -> None:
    parent = ParentLLM(
        [
            parallel_action(
                {"agent_name": "research", "objective": "One."},
                {"agent_name": "data_analyst", "objective": "Two."},
                {"agent_name": "software_engineer", "objective": "Three."},
            ),
            AgentAction(action_type="finish", reasoning_summary="Limit explained.", final_answer="Limited."),
        ]
    )
    calls = 0

    def factory(_definition: AgentDefinition) -> LLMClient:
        nonlocal calls
        calls += 1
        return ChildLLM("unexpected")

    state = await make_runner(parent, factory, max_parallel=2).run("Too many tasks")

    assert calls == 0
    assert state.delegation_requests == []
    assert "max_parallel_subagents (3/2)" in (state.observations[0].content.error or "")


@pytest.mark.asyncio
async def test_invalid_specialist_rejects_the_whole_parallel_action_before_execution() -> None:
    parent = ParentLLM(
        [
            parallel_action(
                {"agent_name": "research", "objective": "Valid task."},
                {"agent_name": "missing", "objective": "Invalid task."},
            ),
            AgentAction(action_type="finish", reasoning_summary="Stop.", final_answer="Invalid."),
        ]
    )
    calls = 0

    def factory(_definition: AgentDefinition) -> LLMClient:
        nonlocal calls
        calls += 1
        return ChildLLM("unexpected")

    state = await make_runner(parent, factory).run("Validate batch")

    assert calls == 0
    assert state.delegation_requests == []
    assert state.observations[0].content.status == "invalid"


@pytest.mark.asyncio
async def test_repeated_identical_delegation_is_blocked_before_a_third_child_run(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    parent = ParentLLM(
        [
            AgentAction(
                action_type="delegate", reasoning_summary="Try research.",
                agent_name="research", objective="Verify the same claim.",
            ),
            AgentAction(
                action_type="delegate", reasoning_summary="Try research again.",
                agent_name="research", objective="Verify the same claim.",
            ),
            AgentAction(
                action_type="delegate", reasoning_summary="Try research repeatedly.",
                agent_name="research", objective="Verify the same claim.",
            ),
            AgentAction(action_type="finish", reasoning_summary="Stop looping.", final_answer="Done."),
        ]
    )
    children_created = 0

    def factory(_definition: AgentDefinition) -> LLMClient:
        nonlocal children_created
        children_created += 1
        return ChildLLM("Same result.")

    state = await make_runner(parent, factory).run("Avoid delegation loops")

    assert state.completed
    assert children_created == 2
    assert state.successful_delegation_count == 2
    assert "repeatedly requested" in (state.observations[2].content.error or "")
    assert any(record.getMessage() == "duplicate_delegation_detected" for record in caplog.records)


@pytest.mark.asyncio
async def test_depth_one_child_cannot_delegate_further() -> None:
    parent = ParentLLM(
        [
            AgentAction(
                action_type="delegate", reasoning_summary="Use research.",
                agent_name="research", objective="Investigate a narrow claim.",
            ),
            AgentAction(action_type="finish", reasoning_summary="Use result.", final_answer="Done."),
        ]
    )
    child = ActionLLM(
        [
            AgentAction(
                action_type="delegate", reasoning_summary="Attempt nesting.",
                agent_name="data_analyst", objective="Nested task.",
            ),
            AgentAction(action_type="finish", reasoning_summary="Report limit.", final_answer="Nested delegation denied."),
        ]
    )

    state = await make_runner(parent, lambda _definition: child).run("Verify depth limit")

    result = state.observations[0].content
    assert isinstance(result, SubagentResult)
    assert result.success
    child_limit = child.contexts[1]["recent_observations"][0]
    assert "max_agent_depth" in child_limit["error"]
    assert "available_specialist_agents" not in child.contexts[0]


@pytest.mark.asyncio
async def test_per_run_delegation_limit_is_enforced_before_a_third_child() -> None:
    parent = ParentLLM(
        [
            AgentAction(action_type="delegate", reasoning_summary="First.", agent_name="research", objective="One."),
            AgentAction(action_type="delegate", reasoning_summary="Second.", agent_name="research", objective="Two."),
            AgentAction(action_type="delegate", reasoning_summary="Third.", agent_name="research", objective="Three."),
            AgentAction(action_type="finish", reasoning_summary="Limits reported.", final_answer="Done."),
        ]
    )

    state = await make_runner(
        parent, lambda _definition: ChildLLM("Complete."), max_delegations=2
    ).run("Bound delegation work")

    assert state.completed
    assert len(state.delegation_requests) == 2
    assert state.successful_delegation_count == 2
    assert "max_delegations_per_run" in (state.observations[2].content.error or "")


@pytest.mark.asyncio
async def test_child_iteration_limit_caps_specialist_work() -> None:
    parent = ParentLLM(
        [
            AgentAction(action_type="delegate", reasoning_summary="Research.", agent_name="research", objective="Loop."),
            AgentAction(action_type="finish", reasoning_summary="Report child limit.", final_answer="Done."),
        ]
    )
    child = ActionLLM(
        [
            AgentAction(
                action_type="use_tool", reasoning_summary="Unavailable tool.",
                tool_name="calculator", tool_arguments={"expression": "1 + 1"},
            )
        ]
    )

    state = await make_runner(
        parent, lambda _definition: child, max_subagent_iterations=1
    ).run("Cap child iterations")

    result = state.observations[0].content
    assert isinstance(result, SubagentResult)
    assert not result.success
    assert result.stop_reason == "max_iterations"
    assert result.iterations == 1
