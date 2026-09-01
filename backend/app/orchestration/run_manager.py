"""Process-local run coordinator and safe trace-to-workbench event projection.

Named for what it manages rather than for the Workbench that first needed it:
every agent run goes through here, whatever interface requested it.
"""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from app.analytics.presentation.chart_store import ChartSpecStore
from app.analytics.presentation.charts import ChartSpec
from app.contracts.answers import AnswerSource
from app.conversations.store import ConversationStore
from app.core.logging import safe_error_message
from app.observability import TraceEvent, TraceEventType, TraceRecorder
from app.orchestration.views import PublicRunEvent, RunMetricsResponse, RunResponse
from app.runtime.runner import AgentRunner
from app.runtime.state import AgentState, RunStatus


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ManagedRun:
    run_id: str
    conversation_id: str
    message: str
    created_at: datetime = field(default_factory=_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    status: str = "running"
    final_response: str | None = None
    error: str | None = None
    charts: list[ChartSpec] = field(default_factory=list)
    sources: list[AnswerSource] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    task: asyncio.Task[None] | None = None


class AgentRunManager:
    """Owns request lifecycle only; traces remain the source of streamed history."""

    def __init__(self, recorder: TraceRecorder, store: ConversationStore | None = None, chart_specs: ChartSpecStore | None = None, *, expose_sql: bool, max_sql_chars: int) -> None:
        self._recorder = recorder
        self._expose_sql = expose_sql
        self._max_sql_chars = max_sql_chars
        self._store = store
        self._chart_specs = chart_specs
        self._runs: dict[str, ManagedRun] = {}

    async def create(self, message: str, conversation_id: str | None, runner: AgentRunner) -> ManagedRun:
        state = AgentState(goal=message)
        if self._store is None:  # Compatibility for isolated runtime tests only.
            managed = ManagedRun(run_id=state.run_id, conversation_id=conversation_id or str(uuid4()), message=message)
        else:
            from uuid import UUID
            conversation, _, _ = await self._store.create_run(
                conversation_id=UUID(conversation_id) if conversation_id else None,
                message=message, run_id=state.run_id,
            )
            managed = ManagedRun(run_id=state.run_id, conversation_id=str(conversation.id), message=message)
        self._runs[managed.run_id] = managed
        managed.task = asyncio.create_task(self._execute(managed, runner, state))
        return managed

    async def _execute(self, managed: ManagedRun, runner: AgentRunner, state: AgentState) -> None:
        managed.started_at = _now()
        if self._store is not None: await self._store.start_run(managed.run_id, managed.started_at)
        try:
            result = await runner.run(managed.message, state=state)
            managed.final_response = result.final_answer
            managed.charts = self._charts_for(managed.run_id)
            managed.sources = list(result.answer_sources)
            managed.caveats = list(result.answer_caveats)
            managed.status = "completed" if result.completed else _public_status(result.status)
            if managed.status == "running":
                # A bounded runtime stop is a failed run from the Workbench's perspective.
                managed.status = "failed"
                managed.error = "The run stopped before producing a final response."
            elif managed.status == "failed":
                managed.error = "The run reached a runtime limit before producing a final response."
        except Exception as error:
            managed.status = "failed"
            managed.error = safe_error_message(error)
        finally:
            managed.finished_at = _now()
            if self._store is not None:
                await self._store.finish_run(
                    run_id=managed.run_id, status=managed.status, completed_at=managed.finished_at,
                    metrics=self._metrics(managed.run_id), error=managed.error,
                    chart_specs=[chart.model_dump(mode="json") for chart in managed.charts],
                    answer_sources=_persisted_sources(managed.sources, managed.status),
                    answer_caveats=_persisted_caveats(managed.caveats, managed.status),
                    assistant_content=managed.final_response if managed.status == "completed" else None,
                )

    async def reconcile_resumed_run(self, result: AgentState) -> None:
        """Persist the terminal state produced after an approval checkpoint resumes."""

        managed = self._runs.get(result.run_id)
        status = "completed" if result.completed else _public_status(result.status)
        error = None if status in {"completed", "waiting_for_approval"} else "The run stopped before producing a final response."
        finished_at = _now()
        if managed is not None:
            managed.status, managed.final_response, managed.error, managed.finished_at = status, result.final_answer, error, finished_at
            managed.charts = self._charts_for(result.run_id)
            managed.sources = list(result.answer_sources)
            managed.caveats = list(result.answer_caveats)
        if self._store is not None:
            await self._store.finish_run(
                run_id=result.run_id, status=status, completed_at=finished_at,
                metrics=self._metrics(result.run_id), error=error,
                chart_specs=[chart.model_dump(mode="json") for chart in self._charts_for(result.run_id)],
                answer_sources=_persisted_sources(result.answer_sources, status),
                answer_caveats=_persisted_caveats(result.answer_caveats, status),
                assistant_content=result.final_answer if status == "completed" else None,
            )

    def get(self, run_id: str) -> ManagedRun | None:
        return self._runs.get(run_id)

    def response(self, managed: ManagedRun) -> RunResponse:
        trace = self._recorder.get_trace(managed.run_id)
        metrics = None
        if trace is not None:
            metrics = RunMetricsResponse.model_validate(trace.metrics.model_dump(include={
                "iterations", "tool_calls", "delegations", "total_duration_ms", "database_query_count",
                "database_rows_returned", "database_rejected_query_count", "total_tokens", "estimated_cost",
            }))
        return RunResponse(run_id=managed.run_id, conversation_id=managed.conversation_id, status=managed.status,
                           created_at=managed.created_at, started_at=managed.started_at,
                           finished_at=managed.finished_at, final_response=managed.final_response,
                           error=managed.error, metrics=metrics, charts=managed.charts,
                           sources=managed.sources, caveats=managed.caveats)

    def _charts_for(self, run_id: str) -> list[ChartSpec]:
        return self._chart_specs.list(run_id) if self._chart_specs is not None else []

    def _metrics(self, run_id: str) -> dict[str, object] | None:
        trace = self._recorder.get_trace(run_id)
        if trace is None: return None
        return trace.metrics.model_dump(include={
            "iterations", "tool_calls", "delegations", "total_duration_ms", "database_query_count",
            "database_rows_returned", "database_rejected_query_count", "total_tokens", "estimated_cost",
        })

    def events(self, managed: ManagedRun) -> list[PublicRunEvent]:
        trace = self._recorder.get_trace(managed.run_id)
        if trace is None:
            return []
        events = [public_event for trace_event in trace.events for public_event in self._project(trace_event, managed)]
        return events

    def _project(self, event: TraceEvent, managed: ManagedRun) -> list[PublicRunEvent]:
        event_type = _PUBLIC_EVENT_TYPES.get(event.event_type)
        if event_type is None:
            return []
        data = _public_data(event, event_type)
        if event_type == "run.completed":
            data["final_response"] = managed.final_response
        elif event_type == "run.failed":
            data["error"] = managed.error or "The run could not be completed."
        if self._expose_sql and event_type.startswith("sql.query") and isinstance(event.metadata.get("sql"), str):
            # SQL is stored only after a successful query and only when the server
            # enabled developer SQL visibility at the execution boundary.
            data["sql"] = event.metadata["sql"][:self._max_sql_chars]
        projected = [PublicRunEvent(id=event.event_id, run_id=event.run_id, type=event_type,
                                    timestamp=event.timestamp, data=data)]
        if event.event_type is TraceEventType.RUN_STARTED:
            projected.append(PublicRunEvent(id=f"{event.event_id}:agent", run_id=event.run_id,
                                             type="agent.started", timestamp=event.timestamp,
                                             data={"agent": "data_analyst"}))
        elif event.event_type is TraceEventType.RUN_FINISHED:
            projected.insert(0, PublicRunEvent(id=f"{event.event_id}:agent", run_id=event.run_id,
                                                type="agent.completed", timestamp=event.timestamp,
                                                data={"agent": "data_analyst"}))
        return projected


def _persisted_sources(
    sources: Sequence[AnswerSource], status: str
) -> list[dict[str, object]] | None:
    """Store the evidence registry only for a run that produced an answer.

    Query identifiers are minted against a process-local trace, so the registry
    is written out in full here rather than left as references that resolve to
    nothing after a restart.
    """

    if status != "completed":
        return None
    return [source.model_dump(mode="json") for source in sources]


def _persisted_caveats(caveats: Sequence[str], status: str) -> list[str] | None:
    """Store stated limitations only for a run that produced an answer.

    A run that stopped short has no answer for a limitation to qualify, so its
    caveats would describe nothing.
    """

    if status != "completed":
        return None
    return list(caveats)


def _public_status(status: RunStatus) -> str:
    return {RunStatus.RUNNING: "running", RunStatus.COMPLETED: "completed",
            RunStatus.FAILED: "failed", RunStatus.WAITING_FOR_APPROVAL: "waiting_for_approval"}[status]


_PUBLIC_EVENT_TYPES = {
    TraceEventType.RUN_STARTED: "run.started", TraceEventType.RUN_FINISHED: "run.completed",
    TraceEventType.RUN_FAILED: "run.failed", TraceEventType.SKILL_LOADED: "skill.loaded",
    TraceEventType.DATABASE_SCHEMA_LISTED: "schema.tables_listed",
    TraceEventType.DATABASE_TABLE_DESCRIBED: "schema.table_described",
    TraceEventType.DATABASE_QUERY_STARTED: "sql.query_started",
    TraceEventType.DATABASE_QUERY_FINISHED: "sql.query_completed",
    TraceEventType.DATABASE_QUERY_FAILED: "sql.query_failed",
    TraceEventType.DATABASE_QUERY_REJECTED: "sql.query_rejected",
    TraceEventType.ANALYTICS_PYTHON_STARTED: "python.analysis_started",
    TraceEventType.ANALYTICS_PYTHON_FINISHED: "python.analysis_completed",
    TraceEventType.ARTIFACT_CREATED: "artifact.created", TraceEventType.CHART_CREATED: "chart.created",
    TraceEventType.REPORT_CREATED: "report.created", TraceEventType.PLAN_UPDATED: "plan.updated",
    TraceEventType.DELEGATION_STARTED: "delegation.started", TraceEventType.DELEGATION_FINISHED: "delegation.completed",
    TraceEventType.TOOL_STARTED: "tool.started", TraceEventType.TOOL_FINISHED: "tool.completed",
    TraceEventType.TOOL_FAILED: "tool.failed", TraceEventType.SECURITY_POLICY_EVALUATED: "security.policy_evaluated",
}


def _public_data(event: TraceEvent, event_type: str) -> dict[str, object]:
    metadata = event.metadata
    if event_type.startswith("sql.query"):
        return {key: metadata[key] for key in ("query_id", "row_count", "truncated", "referenced_tables", "failure_category", "error") if key in metadata} | ({"duration_ms": event.duration_ms} if event.duration_ms is not None else {})
    if event_type.startswith("schema."):
        return {"tables": metadata.get("table_names", [])}
    if event_type == "skill.loaded":
        return {"skill": metadata.get("skill")}
    if event_type in {"artifact.created", "chart.created", "report.created"}:
        return {key: metadata[key] for key in ("artifact_id", "id", "artifact_type", "dataset_id", "report_type") if key in metadata}
    if event_type == "plan.updated":
        return {key: metadata[key] for key in ("plan", "progress") if key in metadata}
    if event_type.startswith("delegation."):
        return {key: metadata[key] for key in ("agent_name", "child_run_id", "child_run_ids") if key in metadata}
    if event_type.startswith("tool."):
        return {key: metadata[key] for key in ("tool_name", "error", "failure_category") if key in metadata} | ({"duration_ms": event.duration_ms} if event.duration_ms is not None else {})
    if event_type == "security.policy_evaluated":
        return {key: metadata[key] for key in ("decision", "capability", "tool_name") if key in metadata}
    return {"status": event.status.value if event.status else None}
