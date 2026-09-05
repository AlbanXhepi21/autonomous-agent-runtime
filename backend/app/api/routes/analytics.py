"""Data Analyst Workbench HTTP and SSE endpoints."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.analytics.presentation.charts import ChartSpec
from app.analytics.presentation.preview import ReportPreview, TemplateSuitabilityOverview
from app.analytics.semantics.metrics import MetricRegistry
from app.api.dependencies import require_csrf, require_permission
from app.api.schemas.analytics import (
    AnswerSource,
    CreateRunRequest,
    CreateRunResponse,
    MetricListResponse,
    MetricSummaryResponse,
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
from app.composition import (
    get_agent_runner,
    get_conversation_store,
    get_metric_registry,
    get_report_publisher,
    get_run_manager,
    get_tenancy_service,
)
from app.conversations.store import ConversationStore
from app.orchestration.publishing import DocumentFormat, ReportPublisher, ReportPublishingError
from app.orchestration.reruns import rerun_query_id
from app.orchestration.run_manager import AgentRunManager
from app.runtime.runner import AgentRunner
from app.tenancy.context import TenantContext
from app.tenancy.contracts import ReportPreferences
from app.tenancy.permissions import Permission
from app.tenancy.service import TenancyService

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/analytics", tags=["analytics-workbench"])

_SYSTEM_DEFAULT_FORMAT: DocumentFormat = "pdf"


async def _resolve_template(
    requested: str | None, *, tenancy: TenancyService, workspace_id: UUID,
) -> str:
    """Explicit request > the workspace's own report-preferences default.

    There is no system-default template: a report has to say what shape it
    wants, from somewhere.
    """

    if requested:
        return requested
    preferences: ReportPreferences = await tenancy.get_report_preferences(workspace_id=workspace_id)
    if preferences.default_template:
        return preferences.default_template
    raise HTTPException(
        status_code=422,
        detail={
            "code": "template_required",
            "message": "No template was given, and this workspace has no default report template configured.",
        },
    )


async def _resolve_formats(
    requested: list[DocumentFormat] | None, *, tenancy: TenancyService, workspace_id: UUID,
) -> list[DocumentFormat]:
    """Explicit request > the workspace's default output format > the system default."""

    if requested:
        return requested
    preferences = await tenancy.get_report_preferences(workspace_id=workspace_id)
    if preferences.default_output_format:
        return [preferences.default_output_format]
    return [_SYSTEM_DEFAULT_FORMAT]


async def _require_owned_run(store: ConversationStore, *, workspace_id, run_id: str) -> None:
    """Verify a bare ``run_id`` belongs to the caller's workspace before using it.

    A run still executing in-process (``manager.get(run_id)``) has not
    necessarily reached the database yet in every code path, but every run
    reachable through this router was created by ``AgentRunManager.create``,
    which persists the owning conversation first -- so this check is always
    meaningful by the time a caller could know the run ID.
    """

    if await store.get_run(workspace_id=workspace_id, run_id=run_id) is None:
        raise HTTPException(status_code=404, detail={"code": "unknown_run", "message": "Run not found."})


@router.post("/runs", response_model=CreateRunResponse, status_code=202, dependencies=[Depends(require_csrf)])
async def create_run(
    request: CreateRunRequest,
    context: TenantContext = Depends(require_permission(Permission.RUN_ANALYSES)),
    runner: AgentRunner = Depends(get_agent_runner),
    manager: AgentRunManager = Depends(get_run_manager),
) -> CreateRunResponse:
    try:
        run = await manager.create(request.message, request.conversation_id, runner, workspace_id=context.workspace.id)
    except (LookupError, ValueError):
        raise HTTPException(status_code=404, detail={"code": "unknown_conversation", "message": "Conversation not found."})
    return CreateRunResponse(run_id=run.run_id, conversation_id=run.conversation_id, status="running")


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    manager: AgentRunManager = Depends(get_run_manager), store: ConversationStore = Depends(get_conversation_store),
) -> RunResponse:
    run = manager.get(run_id)
    if run is not None:
        if run.workspace_id != str(context.workspace.id):
            raise HTTPException(status_code=404, detail={"code": "unknown_run", "message": "Run not found."})
        return manager.response(run)
    persisted = await store.get_run(workspace_id=context.workspace.id, run_id=run_id)
    if persisted is None: raise HTTPException(status_code=404, detail={"code": "unknown_run", "message": "Run not found."})
    assistant_message = await store.get_assistant_message_for_run(workspace_id=context.workspace.id, run_id=run_id)
    return RunResponse(run_id=persisted.id, conversation_id=str(persisted.conversation_id), status=persisted.status,
                       created_at=persisted.created_at, started_at=persisted.started_at, finished_at=persisted.completed_at,
                       final_response=assistant_message.content if assistant_message else None, error=persisted.error,
                       metrics=RunMetricsResponse.model_validate(persisted.metrics) if persisted.metrics else None,
                       charts=[ChartSpec.model_validate(chart) for chart in (getattr(persisted, "chart_specs", None) or [])],
                       sources=[AnswerSource.model_validate(source) for source in (getattr(persisted, "answer_sources", None) or [])],
                       caveats=list(getattr(persisted, "answer_caveats", None) or []))


@router.get("/runs/{run_id}/events")
async def stream_events(
    run_id: str, request: Request, last_event_id: str | None = Header(default=None),
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    manager: AgentRunManager = Depends(get_run_manager), store: ConversationStore = Depends(get_conversation_store),
) -> StreamingResponse:
    run = manager.get(run_id)
    if run is None:
        if await store.get_run(workspace_id=context.workspace.id, run_id=run_id) is not None:
            raise HTTPException(status_code=410, detail={"code": "trace_expired", "message": "The run is retained, but its live trace expired after the server restarted."})
        raise HTTPException(status_code=404, detail={"code": "unknown_run", "message": "Run not found."})
    if run.workspace_id != str(context.workspace.id):
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
async def get_event_history(
    run_id: str,
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    manager: AgentRunManager = Depends(get_run_manager),
) -> PublicRunEventListResponse:
    """Return the same safe public event projection used by SSE for an in-process run."""
    run = manager.get(run_id)
    if run is None or run.workspace_id != str(context.workspace.id):
        raise HTTPException(status_code=404, detail={"code": "trace_unavailable", "message": "Trace is not available for this run."})
    return PublicRunEventListResponse(items=manager.events(run))


@router.get("/runs/{run_id}/report-suitability", response_model=TemplateSuitabilityOverview)
async def get_report_suitability(
    run_id: str, context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    publisher: ReportPublisher = Depends(get_report_publisher),
) -> TemplateSuitabilityOverview:
    """Score every template against a run's own displays, and recommend one.

    Deterministic assembly only: this reads what the run already produced and
    never calls a model. A caller is free to publish a different template than
    the one recommended here, unless that template's own required content is
    still missing.
    """

    try:
        return await publisher.suitability(workspace_id=context.workspace.id, run_id=run_id)
    except ReportPublishingError as error:
        raise HTTPException(status_code=400, detail={"code": "report_not_available", "message": str(error)})


@router.post("/runs/{run_id}/report-preview", response_model=ReportPreview, dependencies=[Depends(require_csrf)])
async def preview_report(
    run_id: str, request: ReportPreviewRequest,
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    publisher: ReportPublisher = Depends(get_report_publisher),
    tenancy: TenancyService = Depends(get_tenancy_service),
) -> ReportPreview:
    """Compile the exact canonical report a publish of the same request would produce.

    No PDF or DOCX is written. Publishing this same request afterward compiles
    through the identical path, so the previewed assignment and the published
    one always match.
    """

    template_name = await _resolve_template(request.template, tenancy=tenancy, workspace_id=context.workspace.id)
    try:
        return await publisher.preview(
            workspace_id=context.workspace.id, run_id=run_id, template_name=template_name, period=request.period,
            title=request.title, metrics=list(request.metrics), narrative=request.narrative,
        )
    except ReportPublishingError as error:
        raise HTTPException(status_code=400, detail={"code": "report_not_previewable", "message": str(error)})


@router.get("/report-templates", response_model=ReportTemplateListResponse)
async def list_report_templates(
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
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
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
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


@router.post("/runs/{run_id}/reports", response_model=PublishReportResponse, status_code=201, dependencies=[Depends(require_csrf)])
async def publish_report(
    run_id: str, request: PublishReportRequest,
    context: TenantContext = Depends(require_permission(Permission.PUBLISH_REPORTS)),
    publisher: ReportPublisher = Depends(get_report_publisher),
    tenancy: TenancyService = Depends(get_tenancy_service),
) -> PublishReportResponse:
    """Assemble a completed run into documents. This never calls the model.

    A caller-supplied ``template``/``formats`` always wins; otherwise this
    falls back to the workspace's own report-preferences default, then a
    system default -- never to the requesting user's personal settings, so a
    published organization report cannot silently vary by who clicked
    publish.
    """

    template_name = await _resolve_template(request.template, tenancy=tenancy, workspace_id=context.workspace.id)
    formats = await _resolve_formats(request.formats, tenancy=tenancy, workspace_id=context.workspace.id)
    try:
        documents = await publisher.publish(
            workspace_id=context.workspace.id, run_id=run_id, template_name=template_name,
            formats=list(formats), period=request.period, title=request.title,
            metrics=list(request.metrics), narrative=request.narrative,
            resolved_locale=context.workspace.default_locale, resolved_timezone=context.workspace.default_timezone,
            resolved_currency=context.workspace.default_currency,
        )
    except ReportPublishingError as error:
        raise HTTPException(status_code=400, detail={"code": "report_not_published", "message": str(error)})
    narrative = request.narrative or ("excluded_from_refreshed_report" if request.metrics else "current")
    return PublishReportResponse(
        run_id=run_id, template=template_name, narrative=narrative,
        rerun_query_ids=[rerun_query_id(index) for index in range(1, len(request.metrics) + 1)],
        documents=[PublishedDocumentResponse(artifact_id=item.id, name=item.name,
                                             media_type=item.media_type, size=item.size)
                   for item in documents],
    )
