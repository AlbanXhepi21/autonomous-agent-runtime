"""The runtime's authority over a run in progress.

A step decides what happened; only this decides that a run ends. Handing it to
a step is what lets the step record a recoverable failure, or read the identity
a run acts under, without reaching back into the loop that owns termination.
"""

import logging

from app.core.limits import RuntimeLimits
from app.core.logging import log_event
from app.runtime.state import AgentState, RunStatus, StopReason
from app.security import SecuritySubject


class RunControl:
    """Terminates runs, counts recoverable failures, and names the acting agent."""

    def __init__(
        self,
        *,
        limits: RuntimeLimits,
        agent_name: str,
        agent_type: str,
        agent_depth: int,
        parent_run_id: str | None,
    ) -> None:
        self._limits = limits
        self._security_agent_name = agent_name
        self._security_agent_type = agent_type
        self._agent_depth = agent_depth
        self._parent_run_id = parent_run_id
        self._logger = logging.getLogger(__name__)

    @property
    def limits(self) -> RuntimeLimits:
        return self._limits

    @property
    def agent_depth(self) -> int:
        return self._agent_depth

    @property
    def agent_name(self) -> str:
        return self._security_agent_name

    def subject(self, state: AgentState) -> SecuritySubject:
        """Construct identity solely from runner and state owned by the runtime."""

        return SecuritySubject(
            agent_name=self._security_agent_name,
            agent_type=self._security_agent_type,
            run_id=state.run_id,
            parent_run_id=self._parent_run_id,
            delegation_depth=self._agent_depth,
        )

    def record_recoverable_error(self, state: AgentState) -> None:
        state.recoverable_error_count += 1
        if state.recoverable_error_count >= self._limits.max_recoverable_errors:
            self.stop(
                state,
                StopReason.TOO_MANY_ERRORS,
                "Agent stopped after reaching the maximum recoverable error limit.",
            )

    def stop(self, state: AgentState, reason: StopReason, answer: str) -> AgentState:
        """Record a runtime-enforced terminal state."""

        state.completed = False
        state.status = RunStatus.FAILED
        state.stop_reason = reason
        state.final_answer = answer
        limit = self._limit_details(state, reason)
        if limit is not None:
            log_event(
                self._logger,
                logging.INFO,
                "runtime_limit_reached",
                run_id=state.run_id,
                resulting_stop_reason=reason,
                **limit,
            )
        return state

    def _limit_details(
        self, state: AgentState, reason: StopReason
    ) -> dict[str, int | str] | None:
        """Return the current and configured value for a runtime limit stop."""

        if reason is StopReason.MAX_ITERATIONS:
            return {
                "limit_type": "max_iterations",
                "current_value": state.iteration_count,
                "configured_limit": self._limits.max_iterations,
            }
        if reason is StopReason.MAX_TOOL_CALLS:
            return {
                "limit_type": "max_tool_calls",
                "current_value": state.total_tool_calls,
                "configured_limit": self._limits.max_tool_calls,
            }
        if reason is StopReason.TOO_MANY_ERRORS:
            return {
                "limit_type": "max_recoverable_errors",
                "current_value": state.recoverable_error_count,
                "configured_limit": self._limits.max_recoverable_errors,
            }
        return None
