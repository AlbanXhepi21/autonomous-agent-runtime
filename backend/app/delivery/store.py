"""Persistence for delivery attempts.

Follows the same shape as every other store in this codebase: an abstract
contract and one PostgreSQL implementation. ``provider_metadata`` is stored
exactly as it arrives from ``DeliveryService`` -- sanitization happens once,
in the provider that produced the response, not here.

``workspace_id`` is a direct column, not inherited through a foreign key --
``artifact_id`` deliberately carries none (the artifact backend is
switchable) -- so every caller-facing method takes it explicitly, matching
the preferred repository pattern.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from app.db.records import DeliveryRecord as DeliveryRow
from app.db.session import Database
from app.delivery.contracts import DeliveryChannel, DeliveryRecord, DeliveryStatus


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_domain(row: DeliveryRow) -> DeliveryRecord:
    return DeliveryRecord(
        id=row.id, workspace_id=row.workspace_id, artifact_id=row.artifact_id, channel=row.channel,
        destination=row.destination, status=row.status, attempt_count=row.attempt_count,
        last_attempt_at=row.last_attempt_at, provider_metadata=dict(row.provider_metadata or {}),
        failure_reason=row.failure_reason, created_at=row.created_at, updated_at=row.updated_at,
    )


class DeliveryStore:
    """Persistence contract for delivery attempts."""

    async def create(
        self, *, workspace_id: UUID, artifact_id: str, channel: DeliveryChannel, destination: str,
    ) -> DeliveryRecord:
        raise NotImplementedError

    async def get(self, *, workspace_id: UUID, delivery_id: UUID) -> DeliveryRecord | None:
        raise NotImplementedError

    async def list(
        self, *, workspace_id: UUID, artifact_id: str | None = None, status: DeliveryStatus | None = None,
    ) -> list[DeliveryRecord]:
        raise NotImplementedError

    async def record_attempt(
        self, *, workspace_id: UUID, delivery_id: UUID, status: DeliveryStatus,
        provider_metadata: dict[str, Any], failure_reason: str | None,
    ) -> DeliveryRecord:
        raise NotImplementedError


class PostgresDeliveryStore(DeliveryStore):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def create(
        self, *, workspace_id: UUID, artifact_id: str, channel: DeliveryChannel, destination: str,
    ) -> DeliveryRecord:
        stamp = _now()
        row = DeliveryRow(
            id=uuid4(), workspace_id=workspace_id, artifact_id=artifact_id, channel=channel,
            destination=destination, status="pending", attempt_count=0, last_attempt_at=None,
            provider_metadata=None, failure_reason=None, created_at=stamp, updated_at=stamp,
        )
        async with self._database.session() as session:
            async with session.begin():
                session.add(row)
        return _to_domain(row)

    async def get(self, *, workspace_id: UUID, delivery_id: UUID) -> DeliveryRecord | None:
        async with self._database.session() as session:
            row = await session.get(DeliveryRow, delivery_id)
        return _to_domain(row) if row is not None and row.workspace_id == workspace_id else None

    async def list(
        self, *, workspace_id: UUID, artifact_id: str | None = None, status: DeliveryStatus | None = None,
    ) -> list[DeliveryRecord]:
        async with self._database.session() as session:
            query = select(DeliveryRow).where(DeliveryRow.workspace_id == workspace_id)
            if artifact_id is not None:
                query = query.where(DeliveryRow.artifact_id == artifact_id)
            if status is not None:
                query = query.where(DeliveryRow.status == status)
            rows = (await session.scalars(query.order_by(DeliveryRow.created_at.desc()))).all()
        return [_to_domain(row) for row in rows]

    async def record_attempt(
        self, *, workspace_id: UUID, delivery_id: UUID, status: DeliveryStatus,
        provider_metadata: dict[str, Any], failure_reason: str | None,
    ) -> DeliveryRecord:
        async with self._database.session() as session:
            async with session.begin():
                row = await session.get(DeliveryRow, delivery_id)
                if row is None or row.workspace_id != workspace_id:
                    raise ValueError(f"Unknown delivery: {delivery_id}")
                row.attempt_count += 1
                row.last_attempt_at = _now()
                row.status = status
                row.provider_metadata = provider_metadata
                row.failure_reason = failure_reason
                row.updated_at = _now()
        return _to_domain(row)
