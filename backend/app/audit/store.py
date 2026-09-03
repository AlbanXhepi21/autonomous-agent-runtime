"""Persistence for the audit log.

Follows the same shape as ``app.identity.store``: an abstract contract, an
in-process implementation for tests and zero-config development, and one
PostgreSQL implementation for a real deployment, selected by
``TENANCY_BACKEND`` (the audit log is tenancy-adjacent, not its own backend
flag -- see ``app.composition.providers.audit``).

Append-only by design: there is no ``update`` or ``delete`` here, on purpose.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from app.audit.contracts import AuditLogEntry
from app.db.records import AuditLogEntryRecord
from app.db.session import Database


def _now() -> datetime:
    return datetime.now(UTC)


class AuditLogStore(ABC):
    @abstractmethod
    async def record(
        self, *, actor_user_id: UUID | None, workspace_id: UUID | None, event_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLogEntry: ...

    @abstractmethod
    async def list_for_workspace(self, *, workspace_id: UUID, limit: int = 50, offset: int = 0) -> list[AuditLogEntry]:
        """Newest first."""

    @abstractmethod
    async def list_for_user(self, *, user_id: UUID, limit: int = 50, offset: int = 0) -> list[AuditLogEntry]:
        """Every event this user was the actor for, across all workspaces. Newest first."""


def _to_domain(record: AuditLogEntryRecord) -> AuditLogEntry:
    return AuditLogEntry(
        id=record.id, actor_user_id=record.actor_user_id, workspace_id=record.workspace_id,
        event_type=record.event_type, metadata=record.event_metadata, created_at=record.created_at,
    )


class InMemoryAuditLogStore(AuditLogStore):
    def __init__(self) -> None:
        self._entries: list[AuditLogEntry] = []
        self._lock = asyncio.Lock()

    async def record(
        self, *, actor_user_id: UUID | None, workspace_id: UUID | None, event_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        async with self._lock:
            entry = AuditLogEntry(
                id=uuid4(), actor_user_id=actor_user_id, workspace_id=workspace_id,
                event_type=event_type, metadata=dict(metadata or {}), created_at=_now(),
            )
            self._entries.append(entry)
            return entry

    async def list_for_workspace(self, *, workspace_id: UUID, limit: int = 50, offset: int = 0) -> list[AuditLogEntry]:
        async with self._lock:
            matches = [item for item in reversed(self._entries) if item.workspace_id == workspace_id]
            return matches[offset:offset + limit]

    async def list_for_user(self, *, user_id: UUID, limit: int = 50, offset: int = 0) -> list[AuditLogEntry]:
        async with self._lock:
            matches = [item for item in reversed(self._entries) if item.actor_user_id == user_id]
            return matches[offset:offset + limit]


class PostgresAuditLogStore(AuditLogStore):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def close(self) -> None:
        await self._database.dispose()

    async def record(
        self, *, actor_user_id: UUID | None, workspace_id: UUID | None, event_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        record = AuditLogEntryRecord(
            id=uuid4(), actor_user_id=actor_user_id, workspace_id=workspace_id,
            event_type=event_type, event_metadata=dict(metadata or {}), created_at=_now(),
        )
        async with self._database.session() as session, session.begin():
            session.add(record)
        return _to_domain(record)

    async def list_for_workspace(self, *, workspace_id: UUID, limit: int = 50, offset: int = 0) -> list[AuditLogEntry]:
        async with self._database.session() as session:
            records = (await session.scalars(
                select(AuditLogEntryRecord).where(AuditLogEntryRecord.workspace_id == workspace_id)
                .order_by(AuditLogEntryRecord.created_at.desc(), AuditLogEntryRecord.id.desc())
                .limit(limit).offset(offset)
            )).all()
        return [_to_domain(record) for record in records]

    async def list_for_user(self, *, user_id: UUID, limit: int = 50, offset: int = 0) -> list[AuditLogEntry]:
        async with self._database.session() as session:
            records = (await session.scalars(
                select(AuditLogEntryRecord).where(AuditLogEntryRecord.actor_user_id == user_id)
                .order_by(AuditLogEntryRecord.created_at.desc(), AuditLogEntryRecord.id.desc())
                .limit(limit).offset(offset)
            )).all()
        return [_to_domain(record) for record in records]
