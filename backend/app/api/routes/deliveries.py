"""Deliver a ready artifact through a configured channel, and see the history.

``DeliveryService.deliver`` already refuses anything that is not ``READY`` --
this router adds nothing on top of that except turning the refusal into an
HTTP error.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas.scheduled_reports import DeliveryResponse, DeliveryTriggerRequest
from app.composition import get_delivery_service, get_delivery_store
from app.delivery.contracts import DeliveryError, DeliveryRecord
from app.delivery.service import DeliveryService
from app.delivery.store import DeliveryStore

router = APIRouter(prefix="/api/v1/deliveries", tags=["deliveries"])


def _to_response(record: DeliveryRecord) -> DeliveryResponse:
    return DeliveryResponse(
        id=str(record.id), artifact_id=record.artifact_id, channel=record.channel,
        destination=record.destination, status=record.status, attempt_count=record.attempt_count,
        last_attempt_at=record.last_attempt_at, provider_metadata=record.provider_metadata,
        failure_reason=record.failure_reason, created_at=record.created_at, updated_at=record.updated_at,
    )


@router.post("", response_model=DeliveryResponse, status_code=201)
async def create_delivery(
    request: DeliveryTriggerRequest, service: DeliveryService = Depends(get_delivery_service),
) -> DeliveryResponse:
    try:
        record = await service.deliver(
            artifact_id=request.artifact_id, channel=request.channel, destination=request.destination,
        )
    except DeliveryError as error:
        raise HTTPException(status_code=422, detail={"code": "delivery_failed", "message": str(error)}) from error
    return _to_response(record)


@router.get("", response_model=list[DeliveryResponse])
async def list_deliveries(
    artifact_id: str | None = Query(default=None), store: DeliveryStore = Depends(get_delivery_store),
) -> list[DeliveryResponse]:
    records = await store.list(artifact_id=artifact_id)
    return [_to_response(record) for record in records]
