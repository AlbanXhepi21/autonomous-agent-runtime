"""Compacting run history once it leaves the recent-observation window.

Summarisation is an optimisation on what the model is shown, so a failure here
leaves the run going with its existing summary rather than ending it.
"""

import logging
from time import perf_counter

from app.runtime.state import AgentState, TaskSummary
from app.runtime.summarization import SummaryPolicy, TaskSummarizer
from app.core.logging import log_event, safe_error_message, safe_log_value
from app.observability import TraceEventType, TraceRecorder


class SummarizationStep:
    """Replaces older observations with a running summary of the task."""

    def __init__(
        self,
        *,
        summarizer: TaskSummarizer,
        policy: SummaryPolicy,
        trace_recorder: TraceRecorder,
    ) -> None:
        self._task_summarizer = summarizer
        self._summary_policy = policy
        self._trace_recorder = trace_recorder
        self._logger = logging.getLogger(__name__)

    async def update(self, state: AgentState) -> None:
        """Summarize only history moving out of the recent-observation window."""

        observations = self._summary_policy.observations_to_summarize(
            state.task_summary, state.observations
        )
        if not observations:
            return
        log_event(
            self._logger, logging.INFO, "task_summary_started", run_id=state.run_id,
            iteration=state.iteration_count, observations_summarized=len(observations),
        )
        summary_span = self._trace_recorder.start_span(state.run_id, TraceEventType.TASK_SUMMARY_STARTED,
            name="task_summary", iteration=state.iteration_count,
            metadata={"observations_summarized": len(observations)})
        started_at = perf_counter()
        current_summary = state.task_summary or TaskSummary(goal=state.goal)
        try:
            summary = await self._task_summarizer.summarize(current_summary, observations)
        except Exception as error:
            self._trace_recorder.finish_span(state.run_id, summary_span, TraceEventType.TASK_SUMMARY_FINISHED,
                iteration=state.iteration_count, success=False, metadata={"error_type": type(error).__name__})
            log_event(
                self._logger, logging.WARNING, "task_summary_failed", run_id=state.run_id,
                iteration=state.iteration_count, observations_summarized=len(observations),
                duration_ms=round((perf_counter() - started_at) * 1000),
                error_type=type(error).__name__, error=safe_error_message(error),
            )
            return
        state.task_summary = summary.model_copy(
            update={
                "goal": state.goal,
                "last_updated_iteration": state.iteration_count,
                "summarized_observation_count": len(state.observations)
                - self._summary_policy.recent_observations,
            }
        )
        log_event(
            self._logger, logging.INFO, "task_summary_updated", run_id=state.run_id,
            iteration=state.iteration_count, observations_summarized=len(observations),
            duration_ms=round((perf_counter() - started_at) * 1000),
            summary_size=len(state.task_summary.model_dump_json()),
        )
        self._trace_recorder.finish_span(state.run_id, summary_span, TraceEventType.TASK_SUMMARY_FINISHED,
            iteration=state.iteration_count, success=True, metadata={"observations_summarized": len(observations)})
        log_event(
            self._logger, logging.DEBUG, "task_summary_content", run_id=state.run_id,
            iteration=state.iteration_count,
            summary=safe_log_value(state.task_summary.model_dump()),
        )
