"""Persistence for scheduled reports, with a claim safe for several workers.

Follows the same shape as ``app.reports.store``: an abstract contract and one
PostgreSQL implementation, every workspace-scoped read and write filtered by
``workspace_id`` in the query itself. ``claim_due`` is the one operation with
no precedent elsewhere in this codebase -- see its docstring for why it is
safe under concurrent workers.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import or_, select, update

from app.db.records import ScheduledReportRecord
from app.db.session import Database
from app.scheduling.contracts import ScheduleConfig, ScheduledReportDefinition


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ScheduledReportNotFoundError(Exception):
    """Raised when a schedule does not exist in the caller's workspace."""


def _to_domain(record: ScheduledReportRecord) -> ScheduledReportDefinition:
    return ScheduledReportDefinition(
        id=record.id, saved_report_id=record.saved_report_id, workspace_id=record.workspace_id,
        schedule=ScheduleConfig.model_validate(record.schedule_config), timezone=record.timezone,
        formats=list(record.formats), delivery_channel=record.delivery_channel,
        delivery_destination=record.delivery_destination, enabled=record.enabled,
        next_run_at=record.next_run_at, last_run_at=record.last_run_at, last_result=record.last_result,
        consecutive_failures=record.consecutive_failures, created_at=record.created_at,
        updated_at=record.updated_at,
    )


class ScheduledReportStore:
    """Persistence contract for scheduled reports and their due-claim queue."""

    async def create(
        self, *, saved_report_id: UUID, workspace_id: str, schedule: ScheduleConfig, timezone: str,
        formats: list[str], delivery_channel: str | None, delivery_destination: str | None,
        next_run_at: datetime,
    ) -> ScheduledReportDefinition:
        raise NotImplementedError

    async def get(self, *, workspace_id: str, scheduled_report_id: UUID) -> ScheduledReportDefinition | None:
        raise NotImplementedError

    async def list(
        self, *, workspace_id: str, enabled: bool | None, limit: int, offset: int,
    ) -> tuple[list[ScheduledReportDefinition], int]:
        raise NotImplementedError

    async def update(
        self, *, workspace_id: str, scheduled_report_id: UUID, changes: dict[str, Any],
    ) -> ScheduledReportDefinition:
        raise NotImplementedError

    async def claim_due(
        self, *, now: datetime, stale_after: timedelta, limit: int,
    ) -> list[ScheduledReportDefinition]:
        """Atomically claim up to ``limit`` due, unclaimed schedules.

        Safe for any number of concurrent workers polling the same table: the
        candidate rows are locked with ``SELECT ... FOR UPDATE SKIP LOCKED``
        inside one transaction, so two workers racing this call can never both
        select the same row -- one gets it, the other's ``SKIP LOCKED``
        silently passes over it and it sees the next candidate instead. The
        claim itself (stamping ``claimed_at``) happens in the same
        transaction, so a row is never visible as "due" to a second worker
        between being selected and being claimed.

        A claim older than ``stale_after`` is treated as abandoned -- a
        worker that claimed a row and then crashed before finishing -- and is
        claimable again, rather than leaving the schedule stuck forever.
        """

        raise NotImplementedError

    async def record_run_result(
        self, *, scheduled_report_id: UUID, ran_at: datetime, result: str, next_run_at: datetime | None,
    ) -> None:
        """Release a claim and record what the run produced.

        ``result`` is ``"completed"``, ``"failed"`` or ``"skipped"``.
        Consecutive failures resets to zero on a completed run, increments on
        a failed one, and is left unchanged for a skip (no run was actually
        attempted, so it is neither a success nor a failure streak entry).
        """

        raise NotImplementedError


class PostgresScheduledReportStore(ScheduledReportStore):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def create(
        self, *, saved_report_id: UUID, workspace_id: str, schedule: ScheduleConfig, timezone: str,
        formats: list[str], delivery_channel: str | None, delivery_destination: str | None,
        next_run_at: datetime,
    ) -> ScheduledReportDefinition:
        stamp = _now()
        record = ScheduledReportRecord(
            id=uuid4(), saved_report_id=saved_report_id, workspace_id=workspace_id,
            schedule_kind=schedule.kind, schedule_config=schedule.model_dump(mode="json"), timezone=timezone,
            formats=list(formats), delivery_channel=delivery_channel, delivery_destination=delivery_destination,
            enabled=True, next_run_at=next_run_at, last_run_at=None, last_result=None,
            consecutive_failures=0, claimed_at=None, created_at=stamp, updated_at=stamp,
        )
        async with self._database.session() as session:
            async with session.begin():
                session.add(record)
        return _to_domain(record)

    async def get(self, *, workspace_id: str, scheduled_report_id: UUID) -> ScheduledReportDefinition | None:
        async with self._database.session() as session:
            record = await session.get(ScheduledReportRecord, scheduled_report_id)
        if record is None or record.workspace_id != workspace_id:
            return None
        return _to_domain(record)

    async def list(
        self, *, workspace_id: str, enabled: bool | None, limit: int, offset: int,
    ) -> tuple[list[ScheduledReportDefinition], int]:
        async with self._database.session() as session:
            query = select(ScheduledReportRecord).where(ScheduledReportRecord.workspace_id == workspace_id)
            if enabled is not None:
                query = query.where(ScheduledReportRecord.enabled.is_(enabled))
            total = len((await session.scalars(query)).all())
            records = (await session.scalars(
                query.order_by(ScheduledReportRecord.next_run_at).limit(limit).offset(offset)
            )).all()
        return [_to_domain(record) for record in records], total

    async def update(
        self, *, workspace_id: str, scheduled_report_id: UUID, changes: dict[str, Any],
    ) -> ScheduledReportDefinition:
        async with self._database.session() as session:
            async with session.begin():
                record = await session.get(ScheduledReportRecord, scheduled_report_id)
                if record is None or record.workspace_id != workspace_id:
                    raise ScheduledReportNotFoundError(str(scheduled_report_id))
                if "schedule" in changes:
                    schedule: ScheduleConfig = changes["schedule"]
                    record.schedule_kind = schedule.kind
                    record.schedule_config = schedule.model_dump(mode="json")
                for field in (
                    "timezone", "formats", "delivery_channel", "delivery_destination",
                    "enabled", "next_run_at",
                ):
                    if field in changes:
                        setattr(record, field, changes[field])
                record.updated_at = _now()
        return _to_domain(record)

    async def claim_due(
        self, *, now: datetime, stale_after: timedelta, limit: int,
    ) -> list[ScheduledReportDefinition]:
        stale_before = now - stale_after
        async with self._database.session() as session:
            async with session.begin():
                candidate_ids = (await session.scalars(
                    select(ScheduledReportRecord.id)
                    .where(ScheduledReportRecord.enabled.is_(True))
                    .where(ScheduledReportRecord.next_run_at <= now)
                    .where(or_(
                        ScheduledReportRecord.claimed_at.is_(None),
                        ScheduledReportRecord.claimed_at < stale_before,
                    ))
                    .order_by(ScheduledReportRecord.next_run_at)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )).all()
                if not candidate_ids:
                    return []
                await session.execute(
                    update(ScheduledReportRecord)
                    .where(ScheduledReportRecord.id.in_(candidate_ids))
                    .values(claimed_at=now)
                )
                records = (await session.scalars(
                    select(ScheduledReportRecord)
                    .where(ScheduledReportRecord.id.in_(candidate_ids))
                    .order_by(ScheduledReportRecord.next_run_at)
                )).all()
        return [_to_domain(record) for record in records]

    async def record_run_result(
        self, *, scheduled_report_id: UUID, ran_at: datetime, result: str, next_run_at: datetime | None,
    ) -> None:
        async with self._database.session() as session:
            async with session.begin():
                record = await session.get(ScheduledReportRecord, scheduled_report_id)
                if record is None:
                    return
                record.last_run_at = ran_at
                record.last_result = result
                if result == "completed":
                    record.consecutive_failures = 0
                elif result == "failed":
                    record.consecutive_failures += 1
                record.claimed_at = None
                if next_run_at is not None:
                    record.next_run_at = next_run_at
                record.updated_at = _now()
