"""Data Analyst Workbench HTTP and SSE endpoints."""

import asyncio

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.analytics.presentation.charts import ChartSpec
from app.analytics.presentation.preview import ReportPreview, TemplateSuitabilityOverview
from app.api.schemas.analytics import AnswerSource
from app.api.schemas.analytics import (
    CreateRunRequest,
    MetricListResponse,
    MetricSummaryResponse,
    CreateRunResponse,
    PublicRunEventListResponse,
    PublishedDocumentResponse,
    PublishReportRequest,
    PublishReportResponse,
    ReportPreviewRequest,
    ReportTemplateListResponse,
    ReportTemplateResponse,
    RunMetricsResponse,
    RunResponse,
)
from app.analytics.semantics.metrics import MetricRegistry
from app.composition import (
    get_agent_runner,
    get_conversation_store,
    get_metric_registry,
    get_report_publisher,
    get_run_manager,
)
from app.conversations.store import ConversationStore
from app.orchestration.publishing import ReportPublisher, ReportPublishingError
from app.orchestration.reruns import rerun_query_id
from app.orchestration.run_manager import AgentRunManager
from app.runtime.runner import AgentRunner

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics-workbench"])


@router.post("/runs", response_model=CreateRunResponse, status_code=202)
async def create_run(request: CreateRunRequest, runner: AgentRunner = Depends(get_agent_runner),
                     manager: AgentRunManager = Depends(get_run_manager)) -> CreateRunResponse:
    try:
        run = await manager.create(request.message, request.conversation_id, runner)
    except (LookupError, ValueError):
        raise HTTPException(status_code=404, detail={"code": "unknown_conversation", "message": "Conversation not found."})
    return CreateRunResponse(run_id=run.run_id, conversation_id=run.conversation_id, status="running")


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, manager: AgentRunManager = Depends(get_run_manager), store: ConversationStore = Depends(get_conversation_store)) -> RunResponse:
    run = manager.get(run_id)
    if run is not None: return manager.response(run)
    persisted = await store.get_run(run_id)
    if persisted is None: raise HTTPException(status_code=404, detail={"code": "unknown_run", "message": "Run not found."})
    assistant_message = await store.get_assistant_message_for_run(run_id)
    return RunResponse(run_id=persisted.id, conversation_id=str(persisted.conversation_id), status=persisted.status,
                       created_at=persisted.created_at, started_at=persisted.started_at, finished_at=persisted.completed_at,
                       final_response=assistant_message.content if assistant_message else None, error=persisted.error,
                       metrics=RunMetricsResponse.model_validate(persisted.metrics) if persisted.metrics else None,
                       charts=[ChartSpec.model_validate(chart) for chart in (getattr(persisted, "chart_specs", None) or [])],
                       sources=[AnswerSource.model_validate(source) for source in (getattr(persisted, "answer_sources", None) or [])],
                       caveats=list(getattr(persisted, "answer_caveats", None) or []))


@router.get("/runs/{run_id}/events")
async def stream_events(run_id: str, request: Request, last_event_id: str | None = Header(default=None),
                        manager: AgentRunManager = Depends(get_run_manager), store: ConversationStore = Depends(get_conversation_store)) -> StreamingResponse:
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
async def get_event_history(run_id: str, manager: AgentRunManager = Depends(get_run_manager)) -> PublicRunEventListResponse:
    """Return the same safe public event projection used by SSE for an in-process run."""
    run = manager.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"code": "trace_unavailable", "message": "Trace is not available for this run."})
    return PublicRunEventListResponse(items=manager.events(run))


@router.get("/runs/{run_id}/report-suitability", response_model=TemplateSuitabilityOverview)
async def get_report_suitability(
    run_id: str, publisher: ReportPublisher = Depends(get_report_publisher),
) -> TemplateSuitabilityOverview:
    """Score every template against a run's own displays, and recommend one.

    Deterministic assembly only: this reads what the run already produced and
    never calls a model. A caller is free to publish a different template than
    the one recommended here, unless that template's own required content is
    still missing.
    """

    try:
        return await publisher.suitability(run_id=run_id)
    except ReportPublishingError as error:
        raise HTTPException(status_code=400, detail={"code": "report_not_available", "message": str(error)})


@router.post("/runs/{run_id}/report-preview", response_model=ReportPreview)
async def preview_report(
    run_id: str, request: ReportPreviewRequest, publisher: ReportPublisher = Depends(get_report_publisher),
) -> ReportPreview:
    """Compile the exact canonical report a publish of the same request would produce.

    No PDF or DOCX is written. Publishing this same request afterward compiles
    through the identical path, so the previewed assignment and the published
    one always match.
    """

    try:
        return await publisher.preview(
            run_id=run_id, template_name=request.template, period=request.period, title=request.title,
            metrics=list(request.metrics), narrative=request.narrative,
        )
    except ReportPublishingError as error:
        raise HTTPException(status_code=400, detail={"code": "report_not_previewable", "message": str(error)})


@router.get("/report-templates", response_model=ReportTemplateListResponse)
async def list_report_templates(
    publisher: ReportPublisher = Depends(get_report_publisher),
) -> ReportTemplateListResponse:
    """Return the document shapes a completed run can be published into."""

    return ReportTemplateListResponse(items=[
        ReportTemplateResponse(
            name=template.name, title=template.title, description=template.description,
            report_type=template.report_type.value,
            period_granularity=template.period_granularity,
            # Structural blocks such as a cover or a page break print no
            # heading, so they are not sections a reader would look for.
            sections=[block.heading for block in template.blocks if block.heading],
        )
        for template in publisher.templates()
    ])


@router.get("/metrics", response_model=MetricListResponse)
async def list_rerunnable_metrics(
    registry: MetricRegistry = Depends(get_metric_registry),
) -> MetricListResponse:
    """Return the metrics a reader may recompute, and what each one accepts.

    The Workbench builds its parameter controls from this, so a reader can only
    choose groupings and filters the definitions already declare.
    """

    return MetricListResponse(items=[
        MetricSummaryResponse(
            name=metric.name, display_name=metric.display_name,
            description=metric.description, unit=metric.unit, format=metric.format,
            dimensions=sorted(metric.dimension_specs), filters=sorted(metric.filter_specs),
            grains=list(metric.supported_grains), value_columns=list(metric.value_columns),
            required_tables=list(metric.required_tables), caveats=list(metric.business_caveats),
            lifecycle_status=metric.status,
        )
        for metric in registry.list_rerunnable()
    ])


@router.post("/runs/{run_id}/reports", response_model=PublishReportResponse, status_code=201)
async def publish_report(
    run_id: str, request: PublishReportRequest,
    publisher: ReportPublisher = Depends(get_report_publisher),
) -> PublishReportResponse:
    """Assemble a completed run into documents. This never calls the model."""

    try:
        documents = await publisher.publish(
            run_id=run_id, template_name=request.template, formats=list(request.formats),
            period=request.period, title=request.title,
            metrics=list(request.metrics), narrative=request.narrative,
        )
    except ReportPublishingError as error:
        raise HTTPException(status_code=400, detail={"code": "report_not_published", "message": str(error)})
    narrative = request.narrative or ("excluded_from_refreshed_report" if request.metrics else "current")
    return PublishReportResponse(
        run_id=run_id, template=request.template, narrative=narrative,
        rerun_query_ids=[rerun_query_id(index) for index in range(1, len(request.metrics) + 1)],
        documents=[PublishedDocumentResponse(artifact_id=item.id, name=item.name,
                                             media_type=item.media_type, size=item.size)
                   for item in documents],
    )
