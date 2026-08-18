"""Provider-neutral, intentional context for LLM action selection."""

from collections.abc import Sequence
from typing import Any, Protocol

from app.agent.state import AgentState, Observation
from app.core.limits import RuntimeLimits
from app.memory.models import Memory
from app.skills.registry import SkillRegistry
from app.tools.registry import ToolRegistry


class ObservationSelector(Protocol):
    """Select the observations that should be visible for one decision."""

    def select(self, observations: Sequence[Observation]) -> list[Observation]:
        """Return observations in the order they should appear in context."""


class RecentObservations:
    """Keep recent detail only after older history is safely summarized."""

    def __init__(self, recent_observations: int = 5) -> None:
        self._recent_observations = recent_observations

    def select(self, observations: Sequence[Observation]) -> list[Observation]:
        return list(observations)

    def select_for_state(self, state: AgentState) -> list[Observation]:
        """Fall back to the full history whenever no valid summary covers it."""

        old_count = max(len(state.observations) - self._recent_observations, 0)
        if (
            state.task_summary is None
            or state.task_summary.summarized_observation_count < old_count
        ):
            return list(state.observations)
        return list(state.observations[-self._recent_observations:])


class ContextBuilder:
    """Build a stable LLM view of runtime state without serializing it wholesale.

    The context keeps task understanding, historical memory, intentional working
    memory, and recent evidence distinct rather than serializing runtime state wholesale.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        skill_registry: SkillRegistry,
        limits: RuntimeLimits,
        observation_selector: ObservationSelector | None = None,
        recent_observations: int = 5,
    ) -> None:
        self._tool_registry = tool_registry
        self._skill_registry = skill_registry
        self._limits = limits
        self._observation_selector = observation_selector or RecentObservations(recent_observations)

    def build(
        self, state: AgentState, *, working_memories: Sequence[Memory] = (),
        relevant_memories: Sequence[Memory] = (),
    ) -> dict[str, Any]:
        """Return only information useful for selecting the next action."""

        return {
            "goal": state.goal,
            "task_summary": state.task_summary.model_dump() if state.task_summary else None,
            "working_memory": [
                {"content": memory.content, "metadata": memory.metadata}
                for memory in working_memories
            ],
            "relevant_memories": [
                {
                    "content": memory.content,
                    "memory_type": memory.memory_type,
                    "metadata": memory.metadata,
                    "created_at": memory.created_at.isoformat(),
                }
                for memory in relevant_memories
            ],
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
            "recent_observations": [
                self._observation_view(observation)
                for observation in self._select_observations(state)
            ],
        }

    def _select_observations(self, state: AgentState) -> list[Observation]:
        if isinstance(self._observation_selector, RecentObservations):
            return self._observation_selector.select_for_state(state)
        return self._observation_selector.select(state.observations)

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
    recent_observations: int = 5,
) -> dict[str, Any]:
    """Build context using the default summary-aware recent-history policy."""

    return ContextBuilder(
        tool_registry,
        skill_registry,
        limits or RuntimeLimits(),
        observation_selector,
        recent_observations,
    ).build(state)
