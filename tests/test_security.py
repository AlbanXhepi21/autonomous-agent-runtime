"""V6.1 coverage for runtime-owned permission decisions."""

from typing import Any

import pytest

from app.agent.definition import AgentDefinition
from app.agent.models import AgentAction
from app.agent.runner import AgentRunner
from app.core.limits import RuntimeLimits
from app.security import (
    Capability, PermissionRule, PolicyDecision, SecurityAction, SecurityPolicy,
    SecuritySubject,
)
from app.skills.registry import SkillRegistry
from app.tools.base import Tool
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry


class CounterTool(Tool):
    def __init__(self, name: str = "write_file") -> None:
        self._name = name
        self.calls = 0

    @property
    def name(self) -> str: return self._name

    @property
    def description(self) -> str: return "Counter."

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"path": {"type": "string"}, "agent_name": {"type": "string"}}, "required": [], "additionalProperties": False}

    async def execute(self, **arguments: Any) -> str:
        self.calls += 1
        return "executed"


def subject(name: str = "primary", agent_type: str = "primary") -> SecuritySubject:
    return SecuritySubject(agent_name=name, agent_type=agent_type, run_id="run-1")


def definition(name: str, allowed_tools: list[str]) -> AgentDefinition:
    return AgentDefinition(
        name=name, description="test", version="1", instructions="test",
        allowed_tools=allowed_tools,
    )


def test_policy_allows_parent_and_derives_specialist_capabilities() -> None:
    policy = SecurityPolicy.primary().with_specialist(definition("data_analyst", ["python_exec"]))

    parent = policy.evaluate(subject(), SecurityAction(capability=Capability.FILESYSTEM_WRITE))
    analyst = policy.evaluate(subject("data_analyst", "specialist"), SecurityAction(capability=Capability.PYTHON_EXECUTE))
    denied = policy.evaluate(subject("data_analyst", "specialist"), SecurityAction(capability=Capability.REPOSITORY_WRITE))

    assert parent.decision is PolicyDecision.ALLOW
    assert analyst.decision is PolicyDecision.ALLOW
    assert denied.decision is PolicyDecision.DENY


def test_policy_denies_unknown_agent_and_unknown_capability() -> None:
    policy = SecurityPolicy.primary()

    unknown_agent = policy.evaluate(subject("unknown", "specialist"), SecurityAction(capability=Capability.FILESYSTEM_READ))
    unknown_capability = policy.evaluate(subject("unknown", "specialist"), SecurityAction(capability=None))

    assert unknown_agent.decision is PolicyDecision.DENY
    assert unknown_capability.decision is PolicyDecision.DENY
    assert unknown_capability.policy_id == "security.unknown_capability"


@pytest.mark.asyncio
async def test_denied_tool_never_executes_and_is_a_safe_observation() -> None:
    tool = CounterTool()
    registry = ToolRegistry()
    registry.register(tool)
    policy = SecurityPolicy.primary().with_specialist(definition("research", []))

    result = await ToolExecutor(registry, security_policy=policy).execute(
        "write_file", {"path": "notes.txt"}, subject=subject("research", "specialist")
    )

    assert not result.success
    assert tool.calls == 0
    assert result.metadata["security_decision"] == "deny"
    assert result.error == "This action is not permitted by runtime security policy."


@pytest.mark.asyncio
async def test_require_approval_never_executes() -> None:
    tool = CounterTool("python_exec")
    registry = ToolRegistry()
    registry.register(tool)
    policy = SecurityPolicy([
        PermissionRule("test.approval", PolicyDecision.REQUIRE_APPROVAL,
                       capability=Capability.PYTHON_EXECUTE, agent_type="primary")
    ])

    result = await ToolExecutor(registry, security_policy=policy).execute(
        "python_exec", {}, subject=subject()
    )

    assert not result.success
    assert tool.calls == 0
    assert result.metadata["security_decision"] == "require_approval"
    assert "human approval" in result.error


@pytest.mark.asyncio
async def test_model_arguments_cannot_forge_subagent_identity() -> None:
    tool = CounterTool("python_exec")
    registry = ToolRegistry()
    registry.register(tool)
    policy = SecurityPolicy.primary().with_specialist(definition("research", []))

    result = await ToolExecutor(registry, security_policy=policy).execute(
        "python_exec", {"agent_name": "data_analyst"},
        subject=subject("research", "specialist"),
    )

    assert not result.success
    assert tool.calls == 0


class ScriptedLLM:
    def __init__(self) -> None:
        self._actions = [
            AgentAction(action_type="use_tool", reasoning_summary="try", tool_name="write_file", tool_arguments={"path": "x"}),
            AgentAction(action_type="finish", reasoning_summary="continue", final_answer="used fallback"),
        ]

    async def choose_action(self, **_: Any) -> AgentAction:
        return self._actions.pop(0)


@pytest.mark.asyncio
async def test_agent_continues_after_security_denial() -> None:
    tool = CounterTool()
    registry = ToolRegistry()
    registry.register(tool)
    policy = SecurityPolicy.primary().with_specialist(definition("research", []))
    runner = AgentRunner(
        ScriptedLLM(), registry, SkillRegistry(), limits=RuntimeLimits(max_iterations=3),
        security_policy=policy, security_agent_name="research", security_agent_type="specialist",
    )

    state = await runner.run("test denial")

    assert state.completed
    assert state.final_answer == "used fallback"
    assert tool.calls == 0
    assert state.observations[0].content.metadata["security_decision"] == "deny"
