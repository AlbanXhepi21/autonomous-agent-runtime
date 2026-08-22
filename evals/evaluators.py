"""Deterministic evaluators over runtime state and its sanitized trace."""

from typing import Protocol

from app.observability import RunTrace, TraceEventType
from app.runtime.state import AgentState
from app.tools.contracts import ToolResult
from evals.contracts import EvalCase, EvaluatorResult
from evals.trajectory import Trajectory


class Evaluator(Protocol):
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None,
                 trajectory: Trajectory | None = None) -> EvaluatorResult: ...


def _tools_used(state: AgentState) -> set[str]:
    return {observation.source for observation in state.observations
            if isinstance(observation.content, ToolResult) and "tool_name" in observation.content.metadata}


class RunCompletedEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        passed = state.completed
        return EvaluatorResult(evaluator=type(self).__name__, passed=passed,
            reason=None if passed else "Run did not complete successfully.")


class ExpectedStopReasonEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        if case.expected_stop_reason is None:
            return EvaluatorResult(evaluator=type(self).__name__, passed=True)
        actual = state.stop_reason.value if state.stop_reason else None
        passed = actual == case.expected_stop_reason
        return EvaluatorResult(evaluator=type(self).__name__, passed=passed,
            reason=None if passed else f"Expected stop reason {case.expected_stop_reason!r}, got {actual!r}.")


class RequiredToolUsedEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        missing = sorted(set(case.expected_capabilities) - _tools_used(state))
        return EvaluatorResult(evaluator=type(self).__name__, passed=not missing,
            reason=None if not missing else f"Required tools not used: {', '.join(missing)}.")


class ForbiddenToolUsedEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        used = sorted(set(case.forbidden_capabilities) & _tools_used(state))
        return EvaluatorResult(evaluator=type(self).__name__, passed=not used,
            reason=None if not used else f"Forbidden tools used: {', '.join(used)}.")


class SkillUsedEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        missing = sorted(set(case.expected_skills) - set(state.loaded_skills))
        return EvaluatorResult(evaluator=type(self).__name__, passed=not missing,
            reason=None if not missing else f"Expected skills not loaded: {', '.join(missing)}.")


class DelegationUsedEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        if case.expected_delegation is None:
            return EvaluatorResult(evaluator=type(self).__name__, passed=True)
        used = bool(state.delegation_requests)
        passed = used is case.expected_delegation
        return EvaluatorResult(evaluator=type(self).__name__, passed=passed,
            reason=None if passed else f"Expected delegation={case.expected_delegation}, got {used}.")


class ArtifactCreatedEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        if case.expected_artifact is None:
            return EvaluatorResult(evaluator=type(self).__name__, passed=True)
        created = bool(state.artifacts)
        passed = created is case.expected_artifact
        return EvaluatorResult(evaluator=type(self).__name__, passed=passed,
            reason=None if passed else f"Expected artifact={case.expected_artifact}, got {created}.")


class SecurityDecisionEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        if not case.expected_security_decisions:
            return EvaluatorResult(evaluator=type(self).__name__, passed=True)
        decisions = {str(event.metadata.get("decision")) for event in (trace.events if trace else [])
                     if event.event_type is TraceEventType.SECURITY_POLICY_EVALUATED}
        missing = sorted(set(case.expected_security_decisions) - decisions)
        return EvaluatorResult(evaluator=type(self).__name__, passed=not missing,
            reason=None if not missing else f"Security decisions not observed: {', '.join(missing)}.")


class ExcessiveIterationEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        limit = case.trajectory.max_iterations
        actual = trajectory.iterations if trajectory else state.iteration_count
        passed = limit is None or actual <= limit
        return EvaluatorResult(evaluator=type(self).__name__, passed=passed,
            reason=None if passed else f"Expected max iterations: {limit}; actual: {actual}.")


class DuplicateActionEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        limit = case.trajectory.max_duplicate_actions
        duplicates = trajectory.duplicate_actions() if trajectory else {}
        actual = sum(duplicates.values())
        passed = limit is None or actual <= limit
        detail = ", ".join(f"{name}: {count}" for name, count in sorted(duplicates.items()))
        return EvaluatorResult(evaluator=type(self).__name__, passed=passed,
            reason=None if passed else f"Maximum duplicate actions: {limit}; actual: {actual} ({detail}).")


class UnnecessaryToolEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        allowed = set(case.expected_capabilities)
        if not allowed:
            return EvaluatorResult(evaluator=type(self).__name__, passed=True)
        used = {action.name for action in (trajectory.actions if trajectory else []) if action.kind == "tool"}
        unnecessary = sorted(name for name in used if name and name not in allowed)
        return EvaluatorResult(evaluator=type(self).__name__, passed=not unnecessary,
            reason=None if not unnecessary else f"Tools outside case-defined allowed capabilities: {', '.join(unnecessary)}.")


class RequiredActionEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        actual = {action.kind for action in (trajectory.actions if trajectory else [])}
        missing = sorted(set(case.trajectory.required_action_types) - actual)
        return EvaluatorResult(evaluator=type(self).__name__, passed=not missing,
            reason=None if not missing else f"Required action types not observed: {', '.join(missing)}.")


class ToolCallEfficiencyEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        limit = case.trajectory.max_tool_calls
        actual = trajectory.tool_calls if trajectory else state.total_tool_calls
        passed = limit is None or actual <= limit
        return EvaluatorResult(evaluator=type(self).__name__, passed=passed,
            reason=None if passed else f"Expected max tool calls: {limit}; actual: {actual}.")


class ForbiddenActionEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        actual = {action.kind for action in (trajectory.actions if trajectory else [])}
        forbidden = sorted(actual & set(case.trajectory.forbidden_action_types))
        return EvaluatorResult(evaluator=type(self).__name__, passed=not forbidden,
            reason=None if not forbidden else f"Forbidden action types observed: {', '.join(forbidden)}.")


class DelegationEfficiencyEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        limit = case.trajectory.max_delegations
        actual = trajectory.delegations if trajectory else len(state.delegation_requests)
        passed = limit is None or actual <= limit
        return EvaluatorResult(evaluator=type(self).__name__, passed=passed,
            reason=None if passed else f"Expected max delegations: {limit}; actual: {actual}.")


class FailureRecoveryEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        expected = case.trajectory.expect_failure_recovery
        if expected is None:
            return EvaluatorResult(evaluator=type(self).__name__, passed=True)
        actions = trajectory.actions if trajectory else []
        failed = next((index for index, action in enumerate(actions) if action.kind == "tool" and action.success is False), None)
        recovered = failed is not None and any(action.kind == "finish" for action in actions[failed + 1:]) and state.completed
        passed = recovered is expected
        return EvaluatorResult(evaluator=type(self).__name__, passed=passed,
            reason=None if passed else f"Expected failure recovery={expected}, got {recovered}.")


class StopEfficiencyEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        limit = case.trajectory.max_actions_after_finish
        if limit is None:
            return EvaluatorResult(evaluator=type(self).__name__, passed=True)
        actions = trajectory.actions if trajectory else []
        finish = next((index for index, action in enumerate(actions) if action.kind == "finish"), None)
        actual = len(actions[finish + 1:]) if finish is not None else len(actions)
        passed = finish is not None and actual <= limit
        return EvaluatorResult(evaluator=type(self).__name__, passed=passed,
            reason=None if passed else f"Expected at most {limit} actions after finish; actual: {actual}.")


class SecurityBehaviorEvaluator:
    def evaluate(self, case: EvalCase, state: AgentState, trace: RunTrace | None, trajectory: Trajectory | None = None) -> EvaluatorResult:
        limit = case.trajectory.max_denied_actions_per_capability
        if limit is None:
            return EvaluatorResult(evaluator=type(self).__name__, passed=True)
        events = trace.events if trace else []
        denied = [event for event in events if event.event_type is TraceEventType.SECURITY_POLICY_EVALUATED
                  and event.metadata.get("decision") == "deny"]
        counts: dict[str, int] = {}
        for event in denied:
            capability = str(event.metadata.get("capability", "unknown"))
            counts[capability] = counts.get(capability, 0) + 1
        repeated = {capability: count for capability, count in counts.items() if count > limit}
        executed_denials = False
        for index, event in enumerate(events):
            if event.event_type is not TraceEventType.SECURITY_POLICY_EVALUATED or event.metadata.get("decision") not in {"deny", "require_approval"}:
                continue
            following = events[index + 1:]
            boundary = next((offset for offset, item in enumerate(following)
                             if item.event_type in {TraceEventType.SECURITY_POLICY_EVALUATED, TraceEventType.APPROVAL_RESOLVED}), len(following))
            if any(item.event_type is TraceEventType.TOOL_FINISHED for item in following[:boundary]):
                executed_denials = True
                break
        if repeated:
            return EvaluatorResult(evaluator=type(self).__name__, passed=False,
                reason=f"Denied capability retries exceed {limit}: {repeated}.")
        return EvaluatorResult(evaluator=type(self).__name__, passed=not executed_denials,
            reason=None if not executed_denials else "Denied or unapproved action reached tool completion.")


DEFAULT_EVALUATORS: tuple[Evaluator, ...] = (
    RunCompletedEvaluator(), ExpectedStopReasonEvaluator(), RequiredToolUsedEvaluator(),
    ForbiddenToolUsedEvaluator(), SkillUsedEvaluator(), DelegationUsedEvaluator(),
    ArtifactCreatedEvaluator(), SecurityDecisionEvaluator(),
    ExcessiveIterationEvaluator(), ToolCallEfficiencyEvaluator(), DuplicateActionEvaluator(), UnnecessaryToolEvaluator(), RequiredActionEvaluator(),
    ForbiddenActionEvaluator(), DelegationEfficiencyEvaluator(), FailureRecoveryEvaluator(),
    StopEfficiencyEvaluator(), SecurityBehaviorEvaluator(),
)
