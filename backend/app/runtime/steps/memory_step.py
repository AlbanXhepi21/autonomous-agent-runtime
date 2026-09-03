"""Everything a run does with memory.

Retrieval, the run-local goal record, and cleanup are each best-effort: memory
is an aid to a run, never a precondition for one, so a failure here leaves the
run usable rather than ending it.
"""

import logging
from time import perf_counter
from uuid import UUID

from app.contracts.runs import CompletedRun
from app.core.logging import log_event, safe_error_message
from app.memory.manager import MemoryManager
from app.memory.records import Memory, MemoryType
from app.memory.retrieval import MemoryRetrievalRequest, MemoryRetriever
from app.memory.writing import MemoryWritingPipeline
from app.observability import TraceEventType, TraceRecorder
from app.security import injection_indicators


class MemoryStep:
    """Reads and writes run memory on behalf of the runtime."""

    def __init__(
        self,
        *,
        manager: MemoryManager | None,
        retriever: MemoryRetriever | None,
        writer: MemoryWritingPipeline | None,
        trace_recorder: TraceRecorder,
    ) -> None:
        self._manager = manager
        self._retriever = retriever
        self._writer = writer
        self._trace_recorder = trace_recorder
        self._logger = logging.getLogger(__name__)

    async def retrieve(self, goal: str, *, run_id: str, workspace_id: str | None, session_id: str | None) -> list[Memory]:
        """Retrieve once per run; a failure leaves the run usable with no history.

        No workspace means no tenant to scope a durable-memory read against,
        so this returns nothing rather than reading unscoped.
        """

        if self._retriever is None or workspace_id is None:
            return []
        log_event(self._logger, logging.INFO, "memory_retrieval_started", run_id=run_id)
        span = self._trace_recorder.start_span(
            run_id, TraceEventType.MEMORY_RETRIEVAL_STARTED, name="memory_retrieval"
        )
        started_at = perf_counter()
        try:
            result = await self._retriever.retrieve(
                MemoryRetrievalRequest(workspace_id=UUID(workspace_id), query=goal, session_id=session_id)
            )
        except Exception as error:
            self._trace_recorder.finish_span(
                run_id, span, TraceEventType.MEMORY_RETRIEVAL_FINISHED, success=False,
                metadata={"returned_count": 0, "error_type": type(error).__name__},
            )
            log_event(
                self._logger, logging.WARNING, "memory_retrieval_failed", run_id=run_id,
                candidate_count=None, returned_count=0,
                duration_ms=round((perf_counter() - started_at) * 1000),
                error_type=type(error).__name__, error=safe_error_message(error),
            )
            return []
        log_event(
            self._logger, logging.INFO, "memory_retrieval_finished", run_id=run_id,
            candidate_count=result.candidate_count, returned_count=len(result.memories),
            duration_ms=round((perf_counter() - started_at) * 1000),
        )
        self._trace_recorder.finish_span(
            run_id, span, TraceEventType.MEMORY_RETRIEVAL_FINISHED, success=True,
            metadata={"candidate_count": result.candidate_count, "returned_count": len(result.memories)},
        )
        for memory in result.memories:
            log_event(
                self._logger, logging.INFO, "untrusted_content_ingested", run_id=run_id,
                source_type="memory", source_identifier=str(memory.id),
            )
            for indicator in injection_indicators(memory.content):
                log_event(
                    self._logger, logging.WARNING, "prompt_injection_indicator_detected",
                    run_id=run_id, source_type="memory", source_identifier=str(memory.id),
                    matched_heuristic=indicator,
                )
        return result.memories

    async def record_goal(self, goal: str, *, run_id: str, workspace_id: str | None) -> None:
        """Keep the submitted goal as run-local working memory."""

        if self._manager is None or workspace_id is None:
            return
        await self._manager.add_working_memory(
            goal, workspace_id=UUID(workspace_id), run_id=run_id, metadata={"kind": "task_goal"},
        )

    async def working(self, run_id: str, *, workspace_id: str | None) -> list[Memory]:
        """Read explicit working memory without exposing store details to context."""

        if self._manager is None or workspace_id is None:
            return []
        return await self._manager.get_memories(MemoryType.WORKING, workspace_id=UUID(workspace_id), run_id=run_id)

    async def capture(self, state: CompletedRun, *, workspace_id: str | None, session_id: str | None) -> None:
        """Offer a completed run to the curated writing pipeline."""

        if self._writer is None:
            return
        await self._writer.capture_completed_run(
            state, workspace_id=UUID(workspace_id) if workspace_id is not None else None, session_id=session_id,
        )

    async def clear(self, run_id: str, *, workspace_id: str | None) -> None:
        """Best-effort cleanup that must not change the agent run result."""

        if self._manager is None or workspace_id is None:
            return
        try:
            await self._manager.clear_working_memory(workspace_id=UUID(workspace_id), run_id=run_id)
        except Exception as error:
            log_event(
                self._logger, logging.WARNING, "working_memory_cleanup_failed", run_id=run_id,
                error_type=type(error).__name__, error=safe_error_message(error),
            )
