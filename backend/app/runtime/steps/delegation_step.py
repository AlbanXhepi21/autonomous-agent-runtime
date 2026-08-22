"""Handing work to a specialist, one delegation or several in parallel.

Validation, limits and duplicate detection happen here; whether a run continues
after a rejected delegation is the runtime's call, so this asks RunControl
rather than deciding for itself.
"""

import logging

from pydantic import ValidationError

from app.contracts.actions import AgentAction
from app.core.exceptions import UnknownAgentError
from app.core.logging import log_event, safe_error_message, safe_log_value
from app.observability import TraceEventType, TraceRecorder
from app.runtime.control import RunControl
from app.runtime.delegation import (
    DelegationContext,
    DelegationExecutor,
    DelegationObservation,
    DelegationRequest,
    ParallelDelegationResult,
    ParallelSubagentExecutor,
    SubagentResult,
)
from app.runtime.fingerprints import delegation_fingerprint
from app.runtime.registry import AgentRegistry
from app.runtime.state import AgentState, Observation
from app.security import (
    Capability,
    PolicyDecision,
    SecurityAction,
    SecurityPolicy,
    SecurityResource,
)


class DelegationStep:
    """Runs model-selected delegations inside the runtime's limits."""

    def __init__(
        self,
        *,
        control: RunControl,
        agent_registry: AgentRegistry | None,
        executor: DelegationExecutor | None,
        parallel_executor: ParallelSubagentExecutor | None,
        security_policy: SecurityPolicy,
        enabled: bool,
        trace_recorder: TraceRecorder,
    ) -> None:
        self._control = control
        self._agent_registry = agent_registry
        self._delegation_executor = executor
        self._parallel_delegation_executor = parallel_executor
        self._security_policy = security_policy
        self._delegation_enabled = enabled
        self._trace_recorder = trace_recorder
        self._logger = logging.getLogger(__name__)

    def _delegation_allowed(self, state: AgentState, target_agent: str) -> bool:
        """Apply the same centralized gate to delegation actions."""

        result = self._security_policy.evaluate(
            self._control.subject(state),
            SecurityAction(
                capability=Capability.AGENT_DELEGATE,
                resource=SecurityResource(resource_type="specialist_agent", identifier=target_agent or "unknown"),
            ),
        )
        fields = {
            "run_id": state.run_id, "agent": self._control.agent_name,
            "capability": Capability.AGENT_DELEGATE.value, "decision": result.decision.value,
            "policy_id": result.policy_id,
        }
        log_event(self._logger, logging.INFO, "risk_assessment_created", **fields,
                  risk_level=result.metadata.get("risk_level"), risk_rule=result.metadata.get("risk_rule"))
        log_event(self._logger, logging.INFO, "security_policy_evaluated", **fields)
        self._trace_recorder.record(state.run_id, TraceEventType.SECURITY_POLICY_EVALUATED,
            iteration=state.iteration_count, success=result.decision == PolicyDecision.ALLOW,
            metadata={"capability": Capability.AGENT_DELEGATE.value, "decision": result.decision.value,
            "policy_id": result.policy_id, "risk_level": result.metadata.get("risk_level")})
        if result.decision == PolicyDecision.ALLOW:
            log_event(self._logger, logging.INFO, "security_action_allowed", **fields)
            return True
        event = "security_approval_required" if result.decision == PolicyDecision.REQUIRE_APPROVAL else "security_action_denied"
        log_event(self._logger, logging.WARNING, event, **fields)
        return False

    async def handle(self, state: AgentState, action: AgentAction) -> None:
        """Validate and execute a model-selected delegation through its boundary."""

        target_agent = action.agent_name if isinstance(action.agent_name, str) else ""
        objective = action.objective if isinstance(action.objective, str) else ""
        if self._control.agent_depth >= self._control.limits.max_agent_depth:
            self._record_delegation_limit(
                state,
                limit_type="max_agent_depth",
                current_value=self._control.agent_depth,
                configured_limit=self._control.limits.max_agent_depth,
            )
            return
        if not self._delegation_allowed(state, target_agent):
            self._record_delegation_observation(
                state, status="invalid", target_agent=target_agent,
                error="Delegation is not permitted by runtime security policy.",
            )
            self._control.record_recoverable_error(state)
            return
        if len(state.delegation_requests) >= self._control.limits.max_delegations_per_run:
            self._record_delegation_limit(
                state,
                limit_type="max_delegations_per_run",
                current_value=len(state.delegation_requests),
                configured_limit=self._control.limits.max_delegations_per_run,
            )
            return
        fingerprint = delegation_fingerprint(target_agent, objective, action.context)
        if self._consecutive_delegation_count(state, fingerprint) >= self._control.limits.max_consecutive_duplicate_actions:
            log_event(
                self._logger,
                logging.INFO,
                "duplicate_delegation_detected",
                run_id=state.run_id,
                iteration=state.iteration_count,
                target_agent=safe_log_value(target_agent),
                duplicate_count=self._consecutive_delegation_count(state, fingerprint) + 1,
                configured_limit=self._control.limits.max_consecutive_duplicate_actions,
            )
            self._record_delegation_observation(
                state,
                status="invalid",
                target_agent=target_agent,
                error="This delegation was repeatedly requested. Use the existing result, change strategy, or finish.",
            )
            self._control.record_recoverable_error(state)
            return
        try:
            request = DelegationRequest(
                parent_run_id=state.run_id,
                parent_iteration=state.iteration_count,
                target_agent=target_agent,
                objective=objective,
                context=DelegationContext(
                    objective=objective,
                    background=action.context,
                    constraints=action.constraints,
                    expected_output=action.expected_output,
                ),
            )
            if self._agent_registry is None:
                raise UnknownAgentError("No specialist agent registry is configured.")
            if not self._delegation_enabled:
                raise UnknownAgentError("Delegation is disabled for this agent run.")
            self._agent_registry.get_metadata(request.target_agent)
        except (ValidationError, UnknownAgentError) as error:
            message = safe_error_message(error)
            log_event(
                self._logger,
                logging.WARNING,
                "delegation_invalid",
                run_id=state.run_id,
                iteration=state.iteration_count,
                target_agent=safe_log_value(target_agent),
                objective=safe_log_value(objective),
                error=message,
            )
            self._record_delegation_observation(
                state,
                status="invalid",
                target_agent=target_agent,
                error=f"Delegation request was rejected: {message}",
            )
            self._control.record_recoverable_error(state)
            return

        state.delegation_requests.append(request)
        state.recent_delegation_fingerprints.append(fingerprint)
        log_event(
            self._logger,
            logging.INFO,
            "delegation_requested",
            run_id=state.run_id,
            iteration=state.iteration_count,
            target_agent=request.target_agent,
            objective=safe_log_value(request.objective),
        )
        delegation_span = self._trace_recorder.start_span(state.run_id, TraceEventType.DELEGATION_STARTED,
            name="delegation", iteration=state.iteration_count,
            metadata={"target_agent": request.target_agent})
        if self._delegation_executor is None:
            self._record_delegation_observation(
                state,
                status="unavailable",
                target_agent=request.target_agent,
                error=(
                    "Delegation was accepted, but child-agent execution is not available "
                    "because no executor is configured. "
                    "Continue the task yourself or choose another action."
                ),
            )
            self._control.record_recoverable_error(state)
            return

        result = await self._delegation_executor.execute(request)
        self._trace_recorder.finish_span(state.run_id, delegation_span, TraceEventType.DELEGATION_FINISHED,
            iteration=state.iteration_count, success=result.success, metadata={"child_run_id": result.child_run_id,
            "target_agent": request.target_agent})
        self._record_subagent_observation(state, result)
        self._account_delegation_results(state, [result])
        if not result.success:
            self._control.record_recoverable_error(state)

    async def handle_parallel(self, state: AgentState, action: AgentAction) -> None:
        """Validate an explicit model-selected batch before concurrent execution."""

        if self._control.agent_depth >= self._control.limits.max_agent_depth:
            self._record_delegation_limit(
                state,
                limit_type="max_agent_depth",
                current_value=self._control.agent_depth,
                configured_limit=self._control.limits.max_agent_depth,
            )
            return
        if not self._delegation_allowed(state, "parallel"):
            self._record_delegation_observation(
                state, status="invalid", target_agent="parallel",
                error="Delegation is not permitted by runtime security policy.",
            )
            self._control.record_recoverable_error(state)
            return
        if not self._delegation_enabled or self._agent_registry is None:
            self._record_delegation_observation(
                state, status="invalid", target_agent="parallel",
                error="Parallel delegation is not available for this agent run.",
            )
            self._control.record_recoverable_error(state)
            return
        if len(action.delegations) > self._control.limits.max_parallel_subagents:
            self._record_delegation_limit(
                state,
                limit_type="max_parallel_subagents",
                current_value=len(action.delegations),
                configured_limit=self._control.limits.max_parallel_subagents,
            )
            return
        if len(state.delegation_requests) + len(action.delegations) > self._control.limits.max_delegations_per_run:
            self._record_delegation_limit(
                state,
                limit_type="max_delegations_per_run",
                current_value=len(state.delegation_requests) + len(action.delegations),
                configured_limit=self._control.limits.max_delegations_per_run,
            )
            return
        try:
            requests = [
                DelegationRequest(
                    parent_run_id=state.run_id,
                    parent_iteration=state.iteration_count,
                    target_agent=item.agent_name,
                    objective=item.objective,
                    context=DelegationContext(
                        objective=item.objective,
                        background=item.context,
                        constraints=item.constraints,
                        expected_output=item.expected_output,
                    ),
                )
                for item in action.delegations
            ]
            for request in requests:
                self._agent_registry.get_metadata(request.target_agent)
        except (AttributeError, ValidationError, UnknownAgentError) as error:
            message = safe_error_message(error)
            log_event(
                self._logger,
                logging.WARNING,
                "delegation_invalid",
                run_id=state.run_id,
                iteration=state.iteration_count,
                target_agent="parallel",
                objective="",
                error=message,
            )
            self._record_delegation_observation(
                state, status="invalid", target_agent="parallel",
                error=f"Delegation request was rejected: {message}",
            )
            self._control.record_recoverable_error(state)
            return
        state.delegation_requests.extend(requests)
        state.parallel_delegation_batch_count += 1
        parallel_span = self._trace_recorder.start_span(state.run_id, TraceEventType.PARALLEL_DELEGATION_STARTED,
            name="parallel_delegation", iteration=state.iteration_count,
            metadata={"delegation_count": len(requests), "target_agents": [request.target_agent for request in requests]})
        if self._parallel_delegation_executor is None:
            self._record_delegation_observation(
                state,
                status="unavailable",
                target_agent="parallel",
                error="Parallel delegation was accepted, but no parallel executor is configured.",
            )
            self._control.record_recoverable_error(state)
            return
        result = await self._parallel_delegation_executor.execute(requests)
        self._trace_recorder.finish_span(state.run_id, parallel_span, TraceEventType.PARALLEL_DELEGATION_FINISHED,
            iteration=state.iteration_count, success=result.success,
            metadata={"child_run_ids": [item.child_run_id for item in result.results]})
        self._record_parallel_subagent_observation(state, result)
        self._account_delegation_results(state, result.results)
        if not result.success:
            self._control.record_recoverable_error(state)

    def _record_delegation_limit(
        self, state: AgentState, *, limit_type: str, current_value: int, configured_limit: int
    ) -> None:
        """Expose a hard delegation boundary to the parent without launching work."""

        log_event(
            self._logger,
            logging.INFO,
            "delegation_limit_reached",
            run_id=state.run_id,
            iteration=state.iteration_count,
            limit_type=limit_type,
            current_value=current_value,
            configured_limit=configured_limit,
        )
        self._record_delegation_observation(
            state,
            status="invalid",
            target_agent="parallel" if limit_type == "max_parallel_subagents" else "delegation",
            error=f"Delegation limit reached: {limit_type} ({current_value}/{configured_limit}).",
        )
        self._control.record_recoverable_error(state)

    @staticmethod
    def _consecutive_delegation_count(state: AgentState, fingerprint: str) -> int:
        count = 0
        for previous in reversed(state.recent_delegation_fingerprints):
            if previous != fingerprint:
                break
            count += 1
        return count

    @staticmethod
    def _account_delegation_results(state: AgentState, results: list[SubagentResult]) -> None:
        state.successful_delegation_count += sum(result.success for result in results)
        state.failed_delegation_count += sum(not result.success for result in results)
        state.child_run_ids.extend(
            result.child_run_id for result in results if result.child_run_id is not None
        )

    @staticmethod
    def _record_delegation_observation(
        state: AgentState, *, status: str, target_agent: str, error: str
    ) -> None:
        """Record a delegation boundary outcome without masquerading as a tool result."""

        state.observations.append(
            Observation(
                source=f"delegation:{target_agent or 'unknown'}",
                content=DelegationObservation(
                    status=status,  # type: ignore[arg-type]
                    target_agent=target_agent,
                    error=error,
                ),
                iteration=state.iteration_count,
                sequence=len(state.observations) + 1,
            )
        )

    @staticmethod
    def _record_subagent_observation(state: AgentState, result: SubagentResult) -> None:
        """Append a child result as a delegation observation, never a tool result."""

        state.observations.append(
            Observation(
                source="subagent",
                content=result,
                iteration=state.iteration_count,
                sequence=len(state.observations) + 1,
            )
        )

    @staticmethod
    def _record_parallel_subagent_observation(
        state: AgentState, result: ParallelDelegationResult
    ) -> None:
        """Append one ordered parallel-result observation for the parent LLM."""

        state.observations.append(
            Observation(
                source="parallel_subagents",
                content=result,
                iteration=state.iteration_count,
                sequence=len(state.observations) + 1,
            )
        )
