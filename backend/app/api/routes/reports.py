"""Durable saved report definitions: create, list, run again.

A saved report is a recipe, never a document -- see ``app.reports.contracts``.
Nothing on this router calls an LLM. A definition whose narrative policy is
``require_new_investigation`` cannot be executed here at all: it is refused
with 409, pointing the caller at starting a normal conversation turn instead,
which is the only place in this application allowed to call a model.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.analytics.presentation.templates import ReportTemplateError, ReportTemplateRegistry
from app.api.dependencies import require_csrf, require_permission
from app.api.schemas.saved_reports import (
    MetricRequestPayload,
    PublishedDocumentSummary,
    RelativePeriodPayload,
    ResolvedParametersResponse,
    SavedReportArchiveRequest,
    SavedReportCreateRequest,
    SavedReportExecuteRequest,
    SavedReportExecuteResponse,
    SavedReportExecutionListResponse,
    SavedReportExecutionResponse,
    SavedReportListResponse,
    SavedReportResponse,
    SavedReportSummaryResponse,
    SavedReportUpdateRequest,
)
from app.artifacts.store import ArtifactStore
from app.composition import (
    get_artifact_store,
    get_report_template_registry,
    get_saved_report_execution_service,
    get_saved_report_store,
)
from app.reports.contracts import RelativePeriod, SavedMetricRequest, SavedReportDefinition
from app.reports.execution import SavedReportExecutionError, SavedReportExecutionService
from app.reports.periods import resolve_relative_period
from app.reports.store import (
    SavedReportNotFoundError,
    SavedReportStore,
    SavedReportVersionConflictError,
)
from app.tenancy.context import TenantContext
from app.tenancy.permissions import Permission

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/reports/saved", tags=["saved-reports"])


def _not_found(saved_report_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "unknown_saved_report", "message": f"Saved report {saved_report_id} not found."},
    )


def _conflict(error: SavedReportVersionConflictError) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={
            "code": "version_conflict",
            "message": f"Expected version {error.expected}, but the saved report is now at version {error.actual}.",
            "expected_version": error.expected,
            "actual_version": error.actual,
        },
    )


def _metric_requests(items: list[MetricRequestPayload]) -> list[SavedMetricRequest]:
    return [SavedMetricRequest(metric=item.metric, dimensions=item.dimensions,
                                filters=item.filters, grain=item.grain) for item in items]


def _period(payload: RelativePeriodPayload) -> RelativePeriod:
    return RelativePeriod(kind=payload.kind, days=payload.days, start=payload.start, end=payload.end)


def _summary(definition: SavedReportDefinition) -> SavedReportSummaryResponse:
    return SavedReportSummaryResponse(
        id=str(definition.id), workspace_id=definition.workspace_id, owner=definition.owner,
        name=definition.name, description=definition.description, template_id=definition.template_id,
        template_version=definition.template_version, narrative_policy=definition.narrative_policy,
        status=definition.status, version=definition.version,
        created_at=definition.created_at, updated_at=definition.updated_at,
    )


def _detail(definition: SavedReportDefinition) -> SavedReportResponse:
    return SavedReportResponse(
        **_summary(definition).model_dump(),
        metric_requests=[MetricRequestPayload(metric=item.metric, dimensions=item.dimensions,
                                               filters=item.filters, grain=item.grain)
                         for item in definition.metric_requests],
        default_period=RelativePeriodPayload(kind=definition.default_period.kind,
                                              days=definition.default_period.days,
                                              start=definition.default_period.start,
                                              end=definition.default_period.end),
        seed_run_id=definition.seed_run_id, seed_narrative=definition.seed_narrative,
        seed_narrative_period=definition.seed_narrative_period,
    )


async def _require_definition(
    store: SavedReportStore, *, workspace_id: UUID, saved_report_id: UUID,
) -> SavedReportDefinition:
    definition = await store.get(workspace_id=workspace_id, saved_report_id=saved_report_id)
    if definition is None:
        raise _not_found(saved_report_id)
    return definition


@router.post("", response_model=SavedReportResponse, status_code=201, dependencies=[Depends(require_csrf)])
async def create_saved_report(
    request: SavedReportCreateRequest,
    context: TenantContext = Depends(require_permission(Permission.PUBLISH_REPORTS)),
    store: SavedReportStore = Depends(get_saved_report_store),
    templates: ReportTemplateRegistry = Depends(get_report_template_registry),
) -> SavedReportResponse:
    """Save a report recipe. The template version pinned is always the current one --

    a caller names a ``template_id``; the version it is pinned to is derived
    here, never accepted from the request, so a saved report can never claim
    to be pinned to a version that never existed.
    """

    try:
        template = templates.get(request.template_id)
    except ReportTemplateError as error:
        raise HTTPException(status_code=400, detail={"code": "unknown_template", "message": str(error)}) from error

    definition = await store.create(
        workspace_id=context.workspace.id, owner=request.owner, name=request.name,
        description=request.description, template_id=request.template_id, template_version=template.version,
        metric_requests=_metric_requests(request.metric_requests), default_period=_period(request.default_period),
        narrative_policy=request.narrative_policy, seed_run_id=request.seed_run_id,
        seed_narrative=request.seed_narrative, seed_narrative_period=request.seed_narrative_period,
    )
    return _detail(definition)


@router.get("", response_model=SavedReportListResponse)
async def list_saved_reports(
    status: str | None = Query(default=None, pattern="^(active|archived)$"),
    limit: int = Query(default=30, ge=1, le=100), offset: int = Query(default=0, ge=0),
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    store: SavedReportStore = Depends(get_saved_report_store),
) -> SavedReportListResponse:
    items, total = await store.list(workspace_id=context.workspace.id, status=status, limit=limit, offset=offset)
    return SavedReportListResponse(items=[_summary(item) for item in items], total=total, limit=limit, offset=offset)


@router.get("/{saved_report_id}", response_model=SavedReportResponse)
async def get_saved_report(
    saved_report_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    store: SavedReportStore = Depends(get_saved_report_store),
) -> SavedReportResponse:
    definition = await _require_definition(store, workspace_id=context.workspace.id, saved_report_id=saved_report_id)
    return _detail(definition)


@router.patch("/{saved_report_id}", response_model=SavedReportResponse, dependencies=[Depends(require_csrf)])
async def update_saved_report(
    saved_report_id: UUID,
    request: SavedReportUpdateRequest,
    context: TenantContext = Depends(require_permission(Permission.PUBLISH_REPORTS)),
    store: SavedReportStore = Depends(get_saved_report_store),
    templates: ReportTemplateRegistry = Depends(get_report_template_registry),
) -> SavedReportResponse:
    """Apply a partial edit. Only parameters and presentation may change here --

    there is no field on this request that lets a caller write a fact a rerun
    would otherwise compute; the metrics, dimensions and filters submitted are
    what get requested again, not a value to display as-is.
    """

    changes = request.model_dump(exclude={"expected_version"}, exclude_unset=True)
    if "template_id" in changes:
        try:
            template = templates.get(changes["template_id"])
        except ReportTemplateError as error:
            raise HTTPException(status_code=400, detail={"code": "unknown_template", "message": str(error)}) from error
        # Re-submitting the same template_id re-pins it to whatever version is
        # current now -- the only way this system lets a caller "accept" a
        # template that moved on since the definition was last saved.
        changes["template_version"] = template.version
    if "metric_requests" in changes:
        changes["metric_requests"] = [item.model_dump(mode="json") for item in
                                       _metric_requests([MetricRequestPayload.model_validate(item)
                                                          for item in changes["metric_requests"]])]
    if "default_period" in changes:
        changes["default_period"] = _period(RelativePeriodPayload.model_validate(
            changes["default_period"])).model_dump(mode="json")

    try:
        definition = await store.update(
            workspace_id=context.workspace.id, saved_report_id=saved_report_id,
            expected_version=request.expected_version, changes=changes,
        )
    except SavedReportNotFoundError as error:
        raise _not_found(saved_report_id) from error
    except SavedReportVersionConflictError as error:
        raise _conflict(error) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": "invalid_update", "message": str(error)}) from error
    return _detail(definition)


@router.post("/{saved_report_id}/archive", response_model=SavedReportResponse, dependencies=[Depends(require_csrf)])
async def archive_saved_report(
    saved_report_id: UUID,
    request: SavedReportArchiveRequest,
    context: TenantContext = Depends(require_permission(Permission.PUBLISH_REPORTS)),
    store: SavedReportStore = Depends(get_saved_report_store),
) -> SavedReportResponse:
    """Archive rather than delete -- a saved report's execution history outlives it."""

    try:
        definition = await store.update(
            workspace_id=context.workspace.id, saved_report_id=saved_report_id,
            expected_version=request.expected_version, changes={"status": "archived"},
        )
    except SavedReportNotFoundError as error:
        raise _not_found(saved_report_id) from error
    except SavedReportVersionConflictError as error:
        raise _conflict(error) from error
    return _detail(definition)


@router.get("/{saved_report_id}/resolved-parameters", response_model=ResolvedParametersResponse)
async def preview_resolved_parameters(
    saved_report_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    store: SavedReportStore = Depends(get_saved_report_store),
    templates: ReportTemplateRegistry = Depends(get_report_template_registry),
) -> ResolvedParametersResponse:
    """What executing this definition right now would use -- no query runs.

    Steps 1-3 of execution only: resolve the period, name the metric requests
    that would be compiled, and say whether the pinned template version still
    matches what is deployed. Nothing here touches the analytics database.
    """

    definition = await _require_definition(store, workspace_id=context.workspace.id, saved_report_id=saved_report_id)
    resolved = resolve_relative_period(definition.default_period, today=datetime.now(timezone.utc).date())
    try:
        current_version = templates.get(definition.template_id).version
    except ReportTemplateError as error:
        raise HTTPException(status_code=400, detail={"code": "unknown_template", "message": str(error)}) from error
    return ResolvedParametersResponse(
        resolved_period_start=resolved.period.start, resolved_period_end=resolved.period.end,
        resolved_period_description=resolved.description,
        metric_requests=[MetricRequestPayload(metric=item.metric, dimensions=item.dimensions,
                                               filters=item.filters, grain=item.grain)
                         for item in definition.metric_requests],
        pinned_template_version=definition.template_version, current_template_version=current_version,
        template_version_matches_pin=current_version == definition.template_version,
    )


def _documents(artifacts) -> list[PublishedDocumentSummary]:
    return [PublishedDocumentSummary(artifact_id=item.id, name=item.name, media_type=item.media_type,
                                      size=item.size) for item in artifacts]


@router.post("/{saved_report_id}/execute", response_model=SavedReportExecuteResponse, dependencies=[Depends(require_csrf)])
async def execute_saved_report(
    saved_report_id: UUID,
    request: SavedReportExecuteRequest,
    context: TenantContext = Depends(require_permission(Permission.PUBLISH_REPORTS)),
    store: SavedReportStore = Depends(get_saved_report_store),
    service: SavedReportExecutionService = Depends(get_saved_report_execution_service),
) -> SavedReportExecuteResponse:
    """Run steps 1-8: resolve, rerun, compile, preview or publish, persist status.

    A definition requiring a new investigation is refused with 409 rather than
    silently starting one -- that policy exists precisely so saving or running
    a report never triggers a model call by itself; a fresh investigation only
    happens when a caller explicitly starts one through the normal chat flow.
    """

    definition = await _require_definition(store, workspace_id=context.workspace.id, saved_report_id=saved_report_id)
    if definition.narrative_policy == "require_new_investigation":
        raise HTTPException(status_code=409, detail={
            "code": "requires_new_investigation",
            "message": "This saved report requires a new agent investigation. Start a new conversation "
                       "turn to produce a fresh narrative; this endpoint never calls a model.",
        })

    try:
        result = await service.execute(
            definition, mode=request.mode, formats=request.formats,
            resolved_locale=context.workspace.default_locale, resolved_timezone=context.workspace.default_timezone,
            resolved_currency=context.workspace.default_currency,
        )
    except SavedReportExecutionError as error:
        execution = await store.create_execution(
            workspace_id=context.workspace.id, saved_report_id=saved_report_id,
            run_id=f"failed-{saved_report_id}-{datetime.now(timezone.utc).timestamp()}",
            mode=request.mode, resolved_period=None, formats=request.formats if request.mode == "publish" else None,
        )
        await store.finish_execution(workspace_id=context.workspace.id, run_id=execution.run_id, status="failed", error=str(error))
        raise HTTPException(status_code=422, detail={"code": "execution_failed", "message": str(error)}) from error

    execution = await store.create_execution(
        workspace_id=context.workspace.id, saved_report_id=saved_report_id, run_id=result.run_id, mode=request.mode,
        resolved_period=(result.resolved.period.start, result.resolved.period.end),
        formats=request.formats if request.mode == "publish" else None,
    )
    await store.finish_execution(workspace_id=context.workspace.id, run_id=result.run_id, status="completed", error=None)

    return SavedReportExecuteResponse(
        execution_id=str(execution.id), run_id=result.run_id, mode=request.mode, status="completed",
        resolved_period_start=result.resolved.period.start, resolved_period_end=result.resolved.period.end,
        preview=result.preview, documents=_documents(result.artifacts),
    )


@router.get("/{saved_report_id}/executions", response_model=SavedReportExecutionListResponse)
async def list_saved_report_executions(
    saved_report_id: UUID,
    limit: int = Query(default=30, ge=1, le=100), offset: int = Query(default=0, ge=0),
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    store: SavedReportStore = Depends(get_saved_report_store),
    artifact_store: ArtifactStore = Depends(get_artifact_store),
) -> SavedReportExecutionListResponse:
    """Every prior run of this saved report, with the artifacts each one produced."""

    outcome = await store.list_executions(
        workspace_id=context.workspace.id, saved_report_id=saved_report_id, limit=limit, offset=offset,
    )
    if outcome is None:
        raise _not_found(saved_report_id)
    executions, total = outcome
    items = []
    for execution in executions:
        artifacts = await artifact_store.list(workspace_id=context.workspace.id, run_id=execution.run_id) if execution.mode == "publish" else []
        items.append(SavedReportExecutionResponse(
            id=str(execution.id), run_id=execution.run_id, mode=execution.mode, status=execution.status,
            resolved_period_start=execution.resolved_period_start, resolved_period_end=execution.resolved_period_end,
            formats=execution.formats, error=execution.error, created_at=execution.created_at,
            completed_at=execution.completed_at, artifacts=_documents(artifacts),
        ))
    return SavedReportExecutionListResponse(items=items, total=total, limit=limit, offset=offset)
