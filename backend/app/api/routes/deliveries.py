"""Deliver a ready artifact through a configured channel, and see the history.

``DeliveryService.deliver`` already refuses anything that is not ``READY`` --
this router adds nothing on top of that except turning the refusal into an
HTTP error.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import require_csrf, require_permission
from app.api.schemas.scheduled_reports import DeliveryResponse, DeliveryTriggerRequest
from app.composition import get_delivery_service, get_delivery_store
from app.delivery.contracts import DeliveryError, DeliveryRecord
from app.delivery.service import DeliveryService
from app.delivery.store import DeliveryStore
from app.tenancy.context import TenantContext
from app.tenancy.permissions import Permission

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/deliveries", tags=["deliveries"])


def _to_response(record: DeliveryRecord) -> DeliveryResponse:
    return DeliveryResponse(
        id=str(record.id), workspace_id=record.workspace_id, artifact_id=record.artifact_id, channel=record.channel,
        destination=record.destination, status=record.status, attempt_count=record.attempt_count,
        last_attempt_at=record.last_attempt_at, provider_metadata=record.provider_metadata,
        failure_reason=record.failure_reason, created_at=record.created_at, updated_at=record.updated_at,
    )


@router.post("", response_model=DeliveryResponse, status_code=201, dependencies=[Depends(require_csrf)])
async def create_delivery(
    request: DeliveryTriggerRequest,
    context: TenantContext = Depends(require_permission(Permission.PUBLISH_REPORTS)),
    service: DeliveryService = Depends(get_delivery_service),
) -> DeliveryResponse:
    try:
        record = await service.deliver(
            workspace_id=context.workspace.id, artifact_id=request.artifact_id, channel=request.channel,
            destination=request.destination,
        )
    except DeliveryError as error:
        raise HTTPException(status_code=422, detail={"code": "delivery_failed", "message": str(error)}) from error
    return _to_response(record)


@router.get("", response_model=list[DeliveryResponse])
async def list_deliveries(
    artifact_id: str | None = Query(default=None),
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    store: DeliveryStore = Depends(get_delivery_store),
) -> list[DeliveryResponse]:
    records = await store.list(workspace_id=context.workspace.id, artifact_id=artifact_id)
    return [_to_response(record) for record in records]
