"""Controlled, provider-neutral autonomous agent loop."""

import asyncio
import logging
from time import perf_counter

from app.agent.context import ContextBuilder
from app.agent.models import AgentAction
from app.agent.policy import tool_action_fingerprint
from app.agent.prompt import SYSTEM_PROMPT
from app.agent.state import AgentState, Observation, StopReason
from app.core.exceptions import UnknownSkillError
from app.core.limits import RuntimeLimits
from app.core.logging import log_event, safe_error_message, safe_log_value
from app.llm.base import LLMClient
from app.skills.registry import SkillRegistry
from app.tools.executor import ToolExecutor
from app.tools.models import ToolResult
from app.tools.registry import ToolRegistry


class AgentRunner:
    """Run dynamic agent actions inside deterministic runtime boundaries."""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        skill_registry: SkillRegistry,
        max_iterations: int | None = None,
        tool_executor: ToolExecutor | None = None,
        limits: RuntimeLimits | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._tool_registry = tool_registry
        self._tool_executor = tool_executor or ToolExecutor(tool_registry)
        self._skill_registry = skill_registry
        self._logger = logging.getLogger(__name__)
        if limits is not None and max_iterations is not None:
            raise ValueError("Provide either limits or max_iterations, not both.")
        self._limits = limits or (
            RuntimeLimits() if max_iterations is None else RuntimeLimits(max_iterations=max_iterations)
        )
        self._context_builder = ContextBuilder(
            tool_registry, skill_registry, self._limits
        )

    async def run(self, goal: str) -> AgentState:
        """Execute bounded, model-selected actions for a single goal."""

        state = AgentState(goal=goal)
        started_at = perf_counter()
        log_event(
            self._logger,
            logging.INFO,
            "agent_run_started",
            run_id=state.run_id,
            goal=safe_log_value(goal),
            max_iterations=self._limits.max_iterations,
            max_tool_calls=self._limits.max_tool_calls,
            max_recoverable_errors=self._limits.max_recoverable_errors,
            max_consecutive_duplicate_actions=self._limits.max_consecutive_duplicate_actions,
        )

        try:
            while state.iteration_count < self._limits.max_iterations:
                iteration = state.iteration_count + 1
                log_event(
                    self._logger,
                    logging.DEBUG,
                    "iteration_started",
                    run_id=state.run_id,
                    iteration=iteration,
                    tool_calls=state.total_tool_calls,
                    errors=state.recoverable_error_count,
                )
                context = self._context_builder.build(state)
                log_event(
                    self._logger,
                    logging.DEBUG,
                    "llm_context_stats",
                    run_id=state.run_id,
                    iteration=iteration,
                    observation_count=len(state.observations),
                    loaded_skill_count=len(state.loaded_skills),
                    available_tool_count=len(context["available_tools"]),
                    available_skill_count=len(context["available_skills"]),
                )
                log_event(
                    self._logger,
                    logging.DEBUG,
                    "llm_request_started",
                    run_id=state.run_id,
                    iteration=iteration,
                )
                llm_started_at = perf_counter()
                action = await self._llm_client.choose_action(
                    system_prompt=SYSTEM_PROMPT,
                    context=context,
                )
                log_event(
                    self._logger,
                    logging.INFO,
                    "llm_action_selected",
                    run_id=state.run_id,
                    iteration=iteration,
                    action=action.action_type,
                    tool=action.tool_name,
                    skill=action.skill_name,
                    duration_ms=round((perf_counter() - llm_started_at) * 1000),
                )
                log_event(
                    self._logger,
                    logging.DEBUG,
                    "llm_action_reasoning_summary",
                    run_id=state.run_id,
                    iteration=iteration,
                    reasoning_summary=safe_log_value(action.reasoning_summary),
                )
                state.iteration_count += 1
                await self._apply_action(state, action)

                if state.completed or state.stop_reason is not None:
                    return self._finish_run(state, started_at)

            return self._finish_run(
                self._stop(
                    state,
                    StopReason.MAX_ITERATIONS,
                    "Agent stopped after reaching the maximum iteration limit.",
                ),
                started_at,
            )
        except Exception as error:
            log_event(
                self._logger,
                logging.ERROR,
                "agent_run_failed",
                run_id=state.run_id,
                iteration=state.iteration_count,
                error_type=type(error).__name__,
                error=safe_error_message(error),
                duration_ms=round((perf_counter() - started_at) * 1000),
            )
            raise

    async def _apply_action(self, state: AgentState, action: AgentAction) -> None:
        """Apply one model-selected action to the current runtime state."""

        if action.action_type == "use_tool":
            tool_name = action.tool_name or ""
            if state.total_tool_calls >= self._limits.max_tool_calls:
                self._stop(
                    state,
                    StopReason.MAX_TOOL_CALLS,
                    "Agent stopped after reaching the maximum tool call limit.",
                )
                return

            fingerprint = tool_action_fingerprint(tool_name, action.tool_arguments)
            duplicate_count = self._consecutive_duplicate_count(state, fingerprint)
            if duplicate_count >= self._limits.max_consecutive_duplicate_actions:
                log_event(
                    self._logger,
                    logging.INFO,
                    "duplicate_action_detected",
                    run_id=state.run_id,
                    iteration=state.iteration_count,
                    action="use_tool",
                    tool=tool_name,
                    duplicate_count=duplicate_count + 1,
                    configured_limit=self._limits.max_consecutive_duplicate_actions,
                )
                self._record_observation(
                    state,
                    source=tool_name,
                    result=ToolResult(
                        success=False,
                        error=(
                            "This tool action has already been attempted repeatedly. "
                            "Use the existing result, change approach, use another tool, "
                            "or finish."
                        ),
                        metadata={"tool_name": tool_name, "duplicate_action": True},
                    ),
                )
                return

            state.recent_action_fingerprints.append(fingerprint)
            state.total_tool_calls += 1
            result = await self._tool_executor.execute(
                tool_name,
                action.tool_arguments,
                run_id=state.run_id,
                iteration=state.iteration_count,
            )
            self._record_observation(state, source=tool_name, result=result)
            if not result.success:
                state.recoverable_error_count += 1
                if state.recoverable_error_count >= self._limits.max_recoverable_errors:
                    self._stop(
                        state,
                        StopReason.TOO_MANY_ERRORS,
                        "Agent stopped after reaching the maximum recoverable error limit.",
                    )
            return

        if action.action_type == "load_skill":
            skill_name = action.skill_name or ""
            log_event(
                self._logger,
                logging.DEBUG,
                "skill_load_requested",
                run_id=state.run_id,
                iteration=state.iteration_count,
                skill=skill_name,
            )
            try:
                if skill_name not in state.loaded_skills:
                    state.loaded_skills[skill_name] = await asyncio.to_thread(
                        self._skill_registry.load_skill, skill_name
                    )
            except UnknownSkillError:
                self._record_observation(
                    state,
                    source=f"skill:{skill_name}",
                    result=ToolResult(
                        success=False,
                        error=safe_error_message(f"Unknown skill: {skill_name}."),
                        metadata={"skill_name": skill_name},
                    ),
                )
                state.recoverable_error_count += 1
                if state.recoverable_error_count >= self._limits.max_recoverable_errors:
                    self._stop(
                        state,
                        StopReason.TOO_MANY_ERRORS,
                        "Agent stopped after reaching the maximum recoverable error limit.",
                    )
                return
            except Exception as error:
                log_event(
                    self._logger,
                    logging.WARNING,
                    "skill_load_failed",
                    run_id=state.run_id,
                    iteration=state.iteration_count,
                    skill=skill_name,
                    error_type=type(error).__name__,
                    error=safe_error_message(error),
                )
                raise
            log_event(
                self._logger,
                logging.INFO,
                "skill_loaded",
                run_id=state.run_id,
                iteration=state.iteration_count,
                skill=skill_name,
            )
            state.recent_action_fingerprints.clear()
            return

        state.final_answer = action.final_answer
        state.completed = True
        state.stop_reason = StopReason.COMPLETED

    @staticmethod
    def _consecutive_duplicate_count(state: AgentState, fingerprint: str) -> int:
        """Count immediately preceding identical tool actions."""

        count = 0
        for previous in reversed(state.recent_action_fingerprints):
            if previous != fingerprint:
                break
            count += 1
        return count

    @staticmethod
    def _record_observation(
        state: AgentState, *, source: str, result: ToolResult
    ) -> None:
        """Append a consistently sequenced execution observation."""

        state.observations.append(
            Observation(
                source=source,
                content=result,
                iteration=state.iteration_count,
                sequence=len(state.observations) + 1,
            )
        )

    def _stop(self, state: AgentState, reason: StopReason, answer: str) -> AgentState:
        """Record a runtime-enforced terminal state."""

        state.completed = False
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

    def _finish_run(self, state: AgentState, started_at: float) -> AgentState:
        """Log the terminal summary for a normal or runtime-limited run."""

        log_event(
            self._logger,
            logging.INFO,
            "agent_finished",
            run_id=state.run_id,
            iterations=state.iteration_count,
            tool_calls=state.total_tool_calls,
            errors=state.recoverable_error_count,
            skills_used=sorted(state.loaded_skills),
            stop_reason=state.stop_reason,
            duration_ms=round((perf_counter() - started_at) * 1000),
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
