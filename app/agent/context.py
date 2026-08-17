"""Provider-neutral, intentional context for LLM action selection."""

from collections.abc import Sequence
from typing import Any, Protocol

from app.agent.state import AgentState, Observation
from app.core.limits import RuntimeLimits
from app.skills.registry import SkillRegistry
from app.tools.registry import ToolRegistry


class ObservationSelector(Protocol):
    """Select the observations that should be visible for one decision."""

    def select(self, observations: Sequence[Observation]) -> list[Observation]:
        """Return observations in the order they should appear in context."""


class AllObservations:
    """Expose every observation until a memory strategy is introduced."""

    def select(self, observations: Sequence[Observation]) -> list[Observation]:
        return list(observations)


class ContextBuilder:
    """Build a stable LLM view of runtime state without serializing it wholesale.

    ``observation_selector`` is the future extension point for recent observations,
    retrieval, and task summaries. The runner does not need to change when that
    policy evolves.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        skill_registry: SkillRegistry,
        limits: RuntimeLimits,
        observation_selector: ObservationSelector | None = None,
    ) -> None:
        self._tool_registry = tool_registry
        self._skill_registry = skill_registry
        self._limits = limits
        self._observation_selector = observation_selector or AllObservations()

    def build(self, state: AgentState) -> dict[str, Any]:
        """Return only information useful for selecting the next action."""

        return {
            "goal": state.goal,
            "runtime_status": self._runtime_status(state),
            "available_tools": self._tool_registry.definitions(),
            "available_skills": [
                skill.model_dump()
                for skill in self._skill_registry.list_skills(
                    exclude_names=state.loaded_skills
                )
            ],
            "loaded_skills": [
                {"name": name, "instructions": instructions}
                for name, instructions in state.loaded_skills.items()
            ],
            "observations": [
                self._observation_view(observation)
                for observation in self._observation_selector.select(state.observations)
            ],
            "recent_errors": [
                self._observation_view(observation)
                for observation in state.observations
                if not observation.content.success
            ],
        }

    def _runtime_status(self, state: AgentState) -> dict[str, int]:
        return {
            "current_iteration": state.iteration_count + 1,
            "maximum_iterations": self._limits.max_iterations,
            "remaining_iterations": max(
                self._limits.max_iterations - state.iteration_count, 0
            ),
            "tool_calls_used": state.total_tool_calls,
            "tool_call_limit": self._limits.max_tool_calls,
            "remaining_tool_calls": max(
                self._limits.max_tool_calls - state.total_tool_calls, 0
            ),
            "recoverable_errors": state.recoverable_error_count,
            "recoverable_error_limit": self._limits.max_recoverable_errors,
            "remaining_recoverable_errors": max(
                self._limits.max_recoverable_errors - state.recoverable_error_count, 0
            ),
        }

    @staticmethod
    def _observation_view(observation: Observation) -> dict[str, Any]:
        """Flatten an execution result into a model-facing observation record."""

        return {
            "sequence": observation.sequence,
            "iteration": observation.iteration,
            "source": observation.source,
            "success": observation.content.success,
            "output": observation.content.output,
            "error": observation.content.error,
        }


def build_context(
    state: AgentState,
    tool_registry: ToolRegistry,
    skill_registry: SkillRegistry,
    limits: RuntimeLimits | None = None,
    observation_selector: ObservationSelector | None = None,
) -> dict[str, Any]:
    """Build context using the default all-observations policy."""

    return ContextBuilder(
        tool_registry,
        skill_registry,
        limits or RuntimeLimits(),
        observation_selector,
    ).build(state)
