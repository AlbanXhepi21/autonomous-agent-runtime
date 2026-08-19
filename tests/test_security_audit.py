"""Adversarial V6 regression checks for concrete bypass and fail-closed behavior."""

from typing import Any

import pytest

from app.security import Capability, PolicyDecision, SecurityPolicy, SecuritySubject
from app.tools.base import Tool
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry


class WriteCounter(Tool):
    def __init__(self) -> None: self.calls = 0
    @property
    def name(self) -> str: return "write_file"
    @property
    def description(self) -> str: return "counter"
    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"], "additionalProperties": False}
    async def execute(self, **_: Any) -> str: self.calls += 1; return "written"


class BrokenPolicy(SecurityPolicy):
    def evaluate(self, subject: SecuritySubject, action: object) -> object:
        raise RuntimeError("policy unavailable")


@pytest.mark.asyncio
async def test_public_executor_cannot_use_removed_approval_flag() -> None:
    tool = WriteCounter(); registry = ToolRegistry(); registry.register(tool)
    policy = SecurityPolicy().with_human_approval_gates([Capability.FILESYSTEM_WRITE])
    executor = ToolExecutor(registry, security_policy=policy)
    subject = SecuritySubject(agent_name="primary", agent_type="primary", run_id="run")

    denied = await executor.execute("write_file", {"path": "x", "content": "x"}, subject=subject)
    assert not denied.success and tool.calls == 0
    with pytest.raises(TypeError):
        await executor.execute("write_file", {"path": "x", "content": "x"}, subject=subject, approval_granted=True)  # type: ignore[call-arg]
    invalid = await executor.execute_approved("write_file", {"path": "x", "content": "x"}, subject=subject)
    assert not invalid.success and tool.calls == 0


@pytest.mark.asyncio
async def test_policy_failure_fails_closed_without_executing_tool() -> None:
    tool = WriteCounter(); registry = ToolRegistry(); registry.register(tool)
    result = await ToolExecutor(registry, security_policy=BrokenPolicy()).execute(
        "write_file", {"path": "x", "content": "x"},
        subject=SecuritySubject(agent_name="primary", agent_type="primary", run_id="run"),
    )
    assert not result.success
    assert result.metadata["policy_id"] == "security.policy_evaluation_failed"
    assert tool.calls == 0
