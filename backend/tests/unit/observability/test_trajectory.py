"""Trace-derived V7.3 trajectory quality coverage."""

from app.observability import RunTrace, TraceEvent, TraceEventType
from app.runtime.state import AgentState, RunStatus, StopReason
from evals.contracts import EvalCase
from evals.evaluators import (
    DelegationEfficiencyEvaluator,
    DuplicateActionEvaluator,
    ExcessiveIterationEvaluator,
    FailureRecoveryEvaluator,
    SecurityBehaviorEvaluator,
    StopEfficiencyEvaluator,
    ToolCallEfficiencyEvaluator,
)
from evals.trajectory import Trajectory


def case(**trajectory: object) -> EvalCase:
    return EvalCase(id="trajectory.test", name="Trajectory", description="Synthetic trace.", goal="Test.", trajectory=trajectory)


def state(*, iterations: int = 1, completed: bool = True) -> AgentState:
    return AgentState(goal="Test.", iteration_count=iterations, completed=completed, status=RunStatus.COMPLETED if completed else RunStatus.FAILED, stop_reason=StopReason.COMPLETED if completed else StopReason.MAX_ITERATIONS)


def trace(*events: TraceEvent, metrics: dict[str, int] | None = None) -> RunTrace:
    return RunTrace(run_id="parent", agent_name="primary", agent_type="primary", goal="Test.", events=list(events), metrics=metrics or {})


def event(event_type: TraceEventType, **kwargs: object) -> TraceEvent:
    return TraceEvent(run_id="parent", event_type=event_type, **kwargs)


def test_efficient_and_duplicate_trajectory() -> None:
    efficient = trace(event(TraceEventType.TOOL_STARTED, metadata={"tool_name": "calculator"}), event(TraceEventType.TOOL_FINISHED, success=True, metadata={"tool_name": "calculator"}), event(TraceEventType.LLM_REQUEST_FINISHED, metadata={"action_type": "finish"}), metrics={"iterations": 2, "tool_calls": 1})
    view = Trajectory.from_trace(efficient)
    assert [action.label for action in view.actions] == ["tool(calculator)", "finish"]
    assert view.llm_decisions == ["finish"]
    assert ToolCallEfficiencyEvaluator().evaluate(case(max_tool_calls=1), state(iterations=2), efficient, view).passed

    repeated = trace(*[event(TraceEventType.TOOL_STARTED, metadata={"tool_name": "calculator"}) for _ in range(3)])
    result = DuplicateActionEvaluator().evaluate(case(max_duplicate_actions=1), state(), repeated, Trajectory.from_trace(repeated))
    assert not result.passed and "actual: 2" in result.reason


def test_iteration_delegation_recovery_stop_and_security_evaluators() -> None:
    recovery = trace(event(TraceEventType.TOOL_STARTED, metadata={"tool_name": "calculator"}), event(TraceEventType.TOOL_FAILED, success=False, metadata={"tool_name": "calculator"}), event(TraceEventType.LLM_REQUEST_FINISHED, metadata={"action_type": "finish"}), metrics={"iterations": 4, "delegations": 1})
    view = Trajectory.from_trace(recovery)
    assert not ExcessiveIterationEvaluator().evaluate(case(max_iterations=3), state(iterations=4), recovery, view).passed
    assert not DelegationEfficiencyEvaluator().evaluate(case(max_delegations=0), state(), recovery, view).passed
    assert FailureRecoveryEvaluator().evaluate(case(expect_failure_recovery=True), state(), recovery, view).passed
    assert StopEfficiencyEvaluator().evaluate(case(max_actions_after_finish=0), state(), recovery, view).passed

    denied = trace(*[event(TraceEventType.SECURITY_POLICY_EVALUATED, metadata={"decision": "deny", "capability": "filesystem.write"}) for _ in range(2)])
    assert not SecurityBehaviorEvaluator().evaluate(case(max_denied_actions_per_capability=1), state(), denied, Trajectory.from_trace(denied)).passed

    executed_denial = trace(event(TraceEventType.SECURITY_POLICY_EVALUATED, metadata={"decision": "deny", "capability": "filesystem.write"}), event(TraceEventType.TOOL_FINISHED, metadata={"tool_name": "write_file"}))
    assert not SecurityBehaviorEvaluator().evaluate(case(max_denied_actions_per_capability=1), state(), executed_denial, Trajectory.from_trace(executed_denial)).passed


def test_parent_child_and_parallel_trajectories_are_accounted_separately() -> None:
    child_one = RunTrace(run_id="child-one", parent_run_id="parent", agent_name="research", agent_type="specialist", goal="Research", metrics={"iterations": 6, "tool_calls": 2})
    child_two = RunTrace(run_id="child-two", parent_run_id="parent", agent_name="analyst", agent_type="specialist", goal="Analyze", metrics={"iterations": 3, "tool_calls": 1})
    parent = trace(event(TraceEventType.PARALLEL_DELEGATION_STARTED, metadata={"delegation_count": 2}), event(TraceEventType.PARALLEL_DELEGATION_FINISHED, metadata={"child_run_ids": ["child-one", "child-two"]}), metrics={"iterations": 4, "tool_calls": 1, "delegations": 2})
    view = Trajectory.from_trace(parent, {"child-one": child_one, "child-two": child_two}.get)
    assert len(view.children) == 2
    assert (view.iterations, view.total_iterations, view.total_tool_calls) == (4, 13, 4)
    assert view.duplicate_actions() == {}
