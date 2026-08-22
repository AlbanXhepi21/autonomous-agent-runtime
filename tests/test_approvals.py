"""V6.2 approval lifecycle tests."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from app.contracts.actions import AgentAction
from app.agent.runner import AgentRunner
from app.agent.state import AgentState, RunStatus
from app.core.limits import RuntimeLimits
from app.security import Capability, PermissionRule, PolicyDecision, SecurityPolicy
from app.security.approvals import ApprovalConflictError, ApprovalRequest, ApprovalStatus, FileApprovalStore
from app.tools.base import Tool
from app.tools.execution import ToolExecutor
from app.tools.registry import ToolRegistry
from tests.support import make_runner
from app.llm.base import LLMClient


class CounterTool(Tool):
    calls = 0
    @property
    def name(self) -> str: return "write_file"
    @property
    def description(self) -> str: return "counter"
    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"], "additionalProperties": False}
    async def execute(self, **_: Any) -> str:
        self.calls += 1; return "written"


class Actions(LLMClient):
    def __init__(self) -> None:
        self.actions = [
            AgentAction(action_type="use_tool", reasoning_summary="write", tool_name="write_file", tool_arguments={"path": "config/app.yaml", "content": "value"}),
            AgentAction(action_type="finish", reasoning_summary="done", final_answer="complete"),
        ]
    async def choose_action(self, **_: Any) -> AgentAction: return self.actions.pop(0)


def runner(tmp_path: Path) -> tuple[AgentRunner, CounterTool, FileApprovalStore]:
    tool = CounterTool(); tool.calls = 0
    registry = ToolRegistry(); registry.register(tool)
    policy = SecurityPolicy([PermissionRule("approval.write", PolicyDecision.REQUIRE_APPROVAL, capability=Capability.FILESYSTEM_WRITE, agent_type="primary")])
    store = FileApprovalStore(tmp_path / "approvals")
    return (
        make_runner(Actions(), registry, limits=RuntimeLimits(max_iterations=4),
                    tool_executor=ToolExecutor(registry, security_policy=policy), security_policy=policy,
                    approval_store=store), tool, store,
    )


@pytest.mark.asyncio
async def test_approval_pauses_then_executes_exact_action_and_resumes(tmp_path: Path) -> None:
    agent, tool, store = runner(tmp_path)
    paused = await agent.run("change config")
    requests = await store.list_for_run(paused.run_id)

    assert paused.status is RunStatus.WAITING_FOR_APPROVAL
    assert tool.calls == 0
    assert len(requests) == 1
    request = requests[0]
    assert request.argument_summary["content_sha256"]
    assert "content" not in request.argument_summary

    await store.resolve(request.id, ApprovalStatus.APPROVED)
    resumed = await agent.resume_approval(request.id)

    assert resumed is not None and resumed.completed
    assert tool.calls == 1
    assert resumed.observations[-1].content.success


@pytest.mark.asyncio
async def test_rejection_never_executes_and_agent_receives_observation(tmp_path: Path) -> None:
    agent, tool, store = runner(tmp_path)
    paused = await agent.run("change config")
    request = (await store.list_for_run(paused.run_id))[0]
    await store.resolve(request.id, ApprovalStatus.REJECTED)
    resumed = await agent.resume_rejection(request.id)

    assert tool.calls == 0
    assert resumed is not None and resumed.completed
    assert "rejected by a human" in resumed.observations[-1].content.error


@pytest.mark.asyncio
async def test_resolution_is_idempotent_but_conflicts_across_decisions(tmp_path: Path) -> None:
    agent, _, store = runner(tmp_path)
    paused = await agent.run("change config")
    request = (await store.list_for_run(paused.run_id))[0]
    assert (await store.resolve(request.id, ApprovalStatus.APPROVED)).status is ApprovalStatus.APPROVED
    assert (await store.resolve(request.id, ApprovalStatus.APPROVED)).status is ApprovalStatus.APPROVED
    with pytest.raises(ApprovalConflictError):
        await store.resolve(request.id, ApprovalStatus.REJECTED)


@pytest.mark.asyncio
async def test_expired_approval_cannot_be_resolved_or_executed(tmp_path: Path) -> None:
    store = FileApprovalStore(tmp_path / "approvals")
    request = ApprovalRequest(run_id="run", agent_name="primary", capability=Capability.FILESYSTEM_WRITE,
                              tool_name="write_file", reason="review", policy_id="p", action_fingerprint="x",
                              expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    from app.security.approvals import ApprovalCheckpoint
    await store.create(request, ApprovalCheckpoint(state={"goal": "x"}, tool_name="write_file", tool_arguments={}, action_fingerprint="x"))
    assert (await store.get(request.id)).status is ApprovalStatus.EXPIRED  # type: ignore[union-attr]
    with pytest.raises(ApprovalConflictError): await store.resolve(request.id, ApprovalStatus.APPROVED)


@pytest.mark.asyncio
async def test_approval_fingerprint_binds_subject_and_exact_arguments(tmp_path: Path) -> None:
    agent, _, store = runner(tmp_path)
    paused = await agent.run("change config")
    request = (await store.list_for_run(paused.run_id))[0]
    checkpoint = await store.checkpoint(request.id)
    assert checkpoint is not None
    assert checkpoint.action_fingerprint == request.action_fingerprint
    assert checkpoint.tool_arguments["content"] == "value"
    assert checkpoint.tool_arguments != {"path": "config/app.yaml", "content": "different"}


@pytest.mark.asyncio
async def test_allowed_action_needs_no_approval_and_child_request_keeps_lineage(tmp_path: Path) -> None:
    tool = CounterTool(); tool.calls = 0
    registry = ToolRegistry(); registry.register(tool)
    allowed = SecurityPolicy([PermissionRule("allow.write", PolicyDecision.ALLOW, capability=Capability.FILESYSTEM_WRITE)])
    direct = make_runner(Actions(), registry, limits=RuntimeLimits(max_iterations=4),
                         tool_executor=ToolExecutor(registry, security_policy=allowed), security_policy=allowed,
                         approval_store=FileApprovalStore(tmp_path / "allowed"))
    assert (await direct.run("write")).completed
    assert tool.calls == 1
    assert await FileApprovalStore(tmp_path / "allowed").list_for_run("missing") == []

    child_policy = SecurityPolicy([PermissionRule("approval.write", PolicyDecision.REQUIRE_APPROVAL, capability=Capability.FILESYSTEM_WRITE)])
    child_store = FileApprovalStore(tmp_path / "child")
    child = make_runner(Actions(), registry, limits=RuntimeLimits(max_iterations=4),
                        tool_executor=ToolExecutor(registry, security_policy=child_policy), security_policy=child_policy,
                        approval_store=child_store, security_agent_name="software_engineer",
                        security_agent_type="specialist", parent_run_id="parent-run", agent_depth=1)
    paused = await child.run("child write", state=AgentState(goal="child write", agent_depth=1))
    request = (await child_store.list_for_run(paused.run_id))[0]
    assert request.parent_run_id == "parent-run"
    assert request.run_id == paused.run_id
    assert request.agent_name == "software_engineer"
