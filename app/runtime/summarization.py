"""Provider-neutral task-summary contracts and deterministic default behavior."""

import json
from dataclasses import dataclass
from typing import Protocol, Sequence

from app.runtime.state import Observation, TaskSummary


class TaskSummarizer(Protocol):
    """Build an updated task summary from a selected observation slice."""

    async def summarize(
        self, current_summary: TaskSummary, observations: Sequence[Observation]
    ) -> TaskSummary:
        """Return the next compact understanding of the task."""


@dataclass(frozen=True, slots=True)
class SummaryPolicy:
    """Deterministic controls for when history becomes a task summary."""

    trigger_observations: int = 8
    recent_observations: int = 5

    def __post_init__(self) -> None:
        if self.trigger_observations < 1:
            raise ValueError("trigger_observations must be at least 1")
        if self.recent_observations < 1:
            raise ValueError("recent_observations must be at least 1")

    def observations_to_summarize(
        self, summary: TaskSummary | None, observations: Sequence[Observation]
    ) -> list[Observation]:
        """Return older observations that would otherwise leave recent context."""

        if len(observations) < self.trigger_observations:
            return []
        old_observation_count = max(len(observations) - self.recent_observations, 0)
        summarized_count = summary.summarized_observation_count if summary else 0
        return list(observations[summarized_count:old_observation_count])


class DeterministicTaskSummarizer:
    """Compact safe observation history without a provider request.

    This default proves the abstraction boundary. A future provider-backed
    implementation can satisfy ``TaskSummarizer`` without changing the runner.
    """

    async def summarize(
        self, current_summary: TaskSummary, observations: Sequence[Observation]
    ) -> TaskSummary:
        """Append concise factual outcomes while retaining prior summary content."""

        progress = list(current_summary.progress)
        failures = list(current_summary.failures_or_blockers)
        for observation in observations:
            outcome = _outcome(observation)
            target = progress if observation.content.success else failures
            if outcome not in target:
                target.append(outcome)
        return current_summary.model_copy(
            update={
                "progress": progress[-8:],
                "failures_or_blockers": failures[-8:],
            }
        )


def _outcome(observation: Observation) -> str:
    value = observation.content.output if observation.content.success else observation.content.error
    rendered = json.dumps(value, default=str, ensure_ascii=False, separators=(",", ":"))
    return f"{observation.source} ({'success' if observation.content.success else 'failed'}): {rendered[:160]}"
