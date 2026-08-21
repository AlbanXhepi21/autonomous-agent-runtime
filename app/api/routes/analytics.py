"""Data Analyst Workbench HTTP and SSE endpoints."""

import asyncio
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.agent.runner import AgentRunner
from app.api.dependencies import get_agent_runner, get_analytics_run_manager, get_conversation_store
from app.api.run_manager import AnalyticsRunManager
from app.api.schemas.analytics import CreateRunRequest, CreateRunResponse, PublicRunEventListResponse, RunMetricsResponse, RunResponse
from app.analytics.charts import ChartSpec
from app.conversations.store import ConversationStore

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics-workbench"])


@router.post("/runs", response_model=CreateRunResponse, status_code=202)
async def create_run(request: CreateRunRequest, runner: AgentRunner = Depends(get_agent_runner),
                     manager: AnalyticsRunManager = Depends(get_analytics_run_manager)) -> CreateRunResponse:
    try:
        run = await manager.create(request.message, request.conversation_id, runner)
    except (LookupError, ValueError):
        raise HTTPException(status_code=404, detail={"code": "unknown_conversation", "message": "Conversation not found."})
    return CreateRunResponse(run_id=run.run_id, conversation_id=run.conversation_id, status="running")


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, manager: AnalyticsRunManager = Depends(get_analytics_run_manager), store: ConversationStore = Depends(get_conversation_store)) -> RunResponse:
    run = manager.get(run_id)
    if run is not None: return manager.response(run)
    persisted = await store.get_run(run_id)
    if persisted is None: raise HTTPException(status_code=404, detail={"code": "unknown_run", "message": "Run not found."})
    assistant_message = await store.get_assistant_message_for_run(run_id)
    return RunResponse(run_id=persisted.id, conversation_id=str(persisted.conversation_id), status=persisted.status,
                       created_at=persisted.created_at, started_at=persisted.started_at, finished_at=persisted.completed_at,
                       final_response=assistant_message.content if assistant_message else None, error=persisted.error,
                       metrics=RunMetricsResponse.model_validate(persisted.metrics) if persisted.metrics else None,
                       charts=[ChartSpec.model_validate(chart) for chart in (getattr(persisted, "chart_specs", None) or [])])


@router.get("/runs/{run_id}/events")
async def stream_events(run_id: str, request: Request, last_event_id: str | None = Header(default=None),
                        manager: AnalyticsRunManager = Depends(get_analytics_run_manager), store: ConversationStore = Depends(get_conversation_store)) -> StreamingResponse:
    run = manager.get(run_id)
    if run is None:
        if await store.get_run(run_id) is not None:
            raise HTTPException(status_code=410, detail={"code": "trace_expired", "message": "The run is retained, but its live trace expired after the server restarted."})
        raise HTTPException(status_code=404, detail={"code": "unknown_run", "message": "Run not found."})

    async def generate():
        delivered = last_event_id
        while True:
            events = manager.events(run)
            start = 0
            if delivered:
                start = next((index + 1 for index, event in enumerate(events) if event.id == delivered), 0)
            for event in events[start:]:
                delivered = event.id
                yield f"id: {event.id}\nevent: {event.type}\ndata: {event.model_dump_json()}\n\n"
            if run.finished_at is not None:
                return
            if await request.is_disconnected():
                return
            yield ": keepalive\n\n"
            await asyncio.sleep(0.25)

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/runs/{run_id}/events/history", response_model=PublicRunEventListResponse)
async def get_event_history(run_id: str, manager: AnalyticsRunManager = Depends(get_analytics_run_manager)) -> PublicRunEventListResponse:
    """Return the same safe public event projection used by SSE for an in-process run."""
    run = manager.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"code": "trace_unavailable", "message": "Trace is not available for this run."})
    return PublicRunEventListResponse(items=manager.events(run))
