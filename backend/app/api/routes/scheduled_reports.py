"""Scheduled saved-report execution: create, list, retrieve, update.

A schedule can only be created for a saved report whose narrative policy is
not ``require_new_investigation`` -- such a report can never execute
deterministically, so scheduling it would only ever produce failures. This
router never calls an LLM and never starts an agent run; it only ever reads
and writes rows describing *when* a saved report should run again.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import require_csrf, require_permission
from app.api.schemas.scheduled_reports import (
    ScheduleConfigPayload,
    ScheduledReportCreateRequest,
    ScheduledReportListResponse,
    ScheduledReportResponse,
    ScheduledReportUpdateRequest,
)
from app.composition import get_saved_report_store, get_scheduled_report_store
from app.reports.store import SavedReportStore
from app.scheduling.calculator import compute_next_run
from app.scheduling.contracts import ScheduleConfig, ScheduledReportDefinition
from app.scheduling.store import ScheduledReportNotFoundError, ScheduledReportStore
from app.tenancy.context import TenantContext
from app.tenancy.permissions import Permission

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/reports/scheduled", tags=["scheduled-reports"])


def _not_found(scheduled_report_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "unknown_scheduled_report", "message": f"Scheduled report {scheduled_report_id} not found."},
    )


def _config(payload: ScheduleConfigPayload) -> ScheduleConfig:
    return ScheduleConfig(
        kind=payload.kind, hour=payload.hour, minute=payload.minute, day_of_week=payload.day_of_week,
        day_of_month=payload.day_of_month, month_of_quarter=payload.month_of_quarter,
    )


def _to_response(definition: ScheduledReportDefinition) -> ScheduledReportResponse:
    return ScheduledReportResponse(
        id=str(definition.id), saved_report_id=str(definition.saved_report_id),
        workspace_id=definition.workspace_id,
        schedule=ScheduleConfigPayload(
            kind=definition.schedule.kind, hour=definition.schedule.hour, minute=definition.schedule.minute,
            day_of_week=definition.schedule.day_of_week, day_of_month=definition.schedule.day_of_month,
            month_of_quarter=definition.schedule.month_of_quarter,
        ),
        timezone=definition.timezone, formats=list(definition.formats),
        delivery_channel=definition.delivery_channel, delivery_destination=definition.delivery_destination,
        enabled=definition.enabled, next_run_at=definition.next_run_at, last_run_at=definition.last_run_at,
        last_result=definition.last_result, consecutive_failures=definition.consecutive_failures,
        created_at=definition.created_at, updated_at=definition.updated_at,
    )


@router.post("", response_model=ScheduledReportResponse, status_code=201, dependencies=[Depends(require_csrf)])
async def create_scheduled_report(
    request: ScheduledReportCreateRequest,
    context: TenantContext = Depends(require_permission(Permission.PUBLISH_REPORTS)),
    schedules: ScheduledReportStore = Depends(get_scheduled_report_store),
    saved_reports: SavedReportStore = Depends(get_saved_report_store),
) -> ScheduledReportResponse:
    definition = await saved_reports.get(workspace_id=context.workspace.id, saved_report_id=request.saved_report_id)
    if definition is None:
        raise HTTPException(status_code=404, detail={
            "code": "unknown_saved_report", "message": f"Saved report {request.saved_report_id} not found.",
        })
    if definition.narrative_policy == "require_new_investigation":
        raise HTTPException(status_code=400, detail={
            "code": "requires_new_investigation",
            "message": "This saved report requires a new agent investigation and can never execute "
                       "deterministically, so it cannot be scheduled.",
        })

    schedule = _config(request.schedule)
    next_run_at = compute_next_run(schedule, tz_name=request.timezone, after=datetime.now(timezone.utc))
    created = await schedules.create(
        saved_report_id=request.saved_report_id, workspace_id=context.workspace.id, schedule=schedule,
        timezone=request.timezone, formats=list(request.formats), delivery_channel=request.delivery_channel,
        delivery_destination=request.delivery_destination, next_run_at=next_run_at,
    )
    return _to_response(created)


@router.get("", response_model=ScheduledReportListResponse)
async def list_scheduled_reports(
    enabled: bool | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    schedules: ScheduledReportStore = Depends(get_scheduled_report_store),
) -> ScheduledReportListResponse:
    items, total = await schedules.list(workspace_id=context.workspace.id, enabled=enabled, limit=limit, offset=offset)
    return ScheduledReportListResponse(items=[_to_response(item) for item in items], total=total, limit=limit, offset=offset)


@router.get("/{scheduled_report_id}", response_model=ScheduledReportResponse)
async def get_scheduled_report(
    scheduled_report_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    schedules: ScheduledReportStore = Depends(get_scheduled_report_store),
) -> ScheduledReportResponse:
    definition = await schedules.get(workspace_id=context.workspace.id, scheduled_report_id=scheduled_report_id)
    if definition is None:
        raise _not_found(scheduled_report_id)
    return _to_response(definition)


@router.patch("/{scheduled_report_id}", response_model=ScheduledReportResponse, dependencies=[Depends(require_csrf)])
async def update_scheduled_report(
    scheduled_report_id: UUID,
    request: ScheduledReportUpdateRequest,
    context: TenantContext = Depends(require_permission(Permission.PUBLISH_REPORTS)),
    schedules: ScheduledReportStore = Depends(get_scheduled_report_store),
) -> ScheduledReportResponse:
    if (request.delivery_channel is None) != (request.delivery_destination is None):
        raise HTTPException(status_code=422, detail={
            "code": "invalid_delivery", "message": "delivery_channel and delivery_destination must be set together.",
        })

    existing = await schedules.get(workspace_id=context.workspace.id, scheduled_report_id=scheduled_report_id)
    if existing is None:
        raise _not_found(scheduled_report_id)

    changes: dict[str, object] = {}
    new_schedule = _config(request.schedule) if request.schedule is not None else existing.schedule
    new_timezone = request.timezone or existing.timezone
    if request.schedule is not None:
        changes["schedule"] = new_schedule
    if request.timezone is not None:
        changes["timezone"] = request.timezone
    if request.schedule is not None or request.timezone is not None:
        # A changed rule or clock means the previously computed next_run_at
        # no longer describes what this schedule actually means.
        changes["next_run_at"] = compute_next_run(new_schedule, tz_name=new_timezone, after=datetime.now(timezone.utc))
    if request.formats is not None:
        changes["formats"] = list(request.formats)
    if request.delivery_channel is not None or request.delivery_destination is not None:
        changes["delivery_channel"] = request.delivery_channel
        changes["delivery_destination"] = request.delivery_destination
    if request.enabled is not None:
        changes["enabled"] = request.enabled

    try:
        updated = await schedules.update(workspace_id=context.workspace.id, scheduled_report_id=scheduled_report_id, changes=changes)
    except ScheduledReportNotFoundError as error:
        raise _not_found(scheduled_report_id) from error
    return _to_response(updated)
