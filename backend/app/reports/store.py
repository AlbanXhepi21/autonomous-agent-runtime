"""Persistence for saved report definitions and their execution history.

Follows the same shape as ``app.conversations.store``: an abstract contract
naming the operations, and one PostgreSQL implementation behind it. Every
operation that reads or writes a specific definition is scoped by
``workspace_id`` in the query itself -- a row from another workspace is
treated exactly like a row that does not exist, never surfaced and never
distinguished from a genuine 404. ``saved_report_executions`` is a child
resource: it carries no ``workspace_id`` of its own and is verified by
joining to its parent ``saved_reports`` row, the same pattern
``app.conversations.store`` uses for messages and runs.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.db.records import SavedReportExecutionRecord, SavedReportRecord
from app.db.session import Database
from app.reports.contracts import (
    RelativePeriod,
    SavedMetricRequest,
    SavedReportDefinition,
    SavedReportExecution,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SavedReportNotFoundError(Exception):
    """Raised when a definition does not exist in the caller's workspace."""


class SavedReportVersionConflictError(Exception):
    """Raised when an update's expected version does not match the stored one."""

    def __init__(self, *, expected: int, actual: int) -> None:
        super().__init__(f"Expected version {expected}, but the stored version is {actual}.")
        self.expected = expected
        self.actual = actual


def _to_domain(record: SavedReportRecord) -> SavedReportDefinition:
    return SavedReportDefinition(
        id=record.id, workspace_id=record.workspace_id, owner=record.owner,
        name=record.name, description=record.description,
        template_id=record.template_id, template_version=record.template_version,
        metric_requests=[SavedMetricRequest.model_validate(item) for item in record.metric_requests],
        default_period=RelativePeriod.model_validate(record.default_period),
        narrative_policy=record.narrative_policy,
        seed_run_id=record.seed_run_id, seed_narrative=record.seed_narrative,
        seed_narrative_period=record.seed_narrative_period,
        version=record.version, status=record.status,
        created_at=record.created_at, updated_at=record.updated_at,
    )


def _execution_to_domain(record: SavedReportExecutionRecord) -> SavedReportExecution:
    return SavedReportExecution(
        id=record.id, saved_report_id=record.saved_report_id,
        scheduled_report_id=record.scheduled_report_id, run_id=record.run_id,
        mode=record.mode, status=record.status,
        resolved_period_start=record.resolved_period_start, resolved_period_end=record.resolved_period_end,
        formats=list(record.formats) if record.formats is not None else None,
        error=record.error, error_category=record.error_category, retry_count=record.retry_count,
        usage_metadata=dict(record.usage_metadata or {}), artifact_ids=list(record.artifact_ids or []),
        created_at=record.created_at, completed_at=record.completed_at,
    )


class SavedReportStore:
    """Persistence contract for saved report definitions and their executions."""

    async def create(
        self, *, workspace_id: UUID, owner: str | None, name: str, description: str | None,
        template_id: str, template_version: str, metric_requests: list[SavedMetricRequest],
        default_period: RelativePeriod, narrative_policy: str,
        seed_run_id: str | None, seed_narrative: str | None, seed_narrative_period: str | None,
    ) -> SavedReportDefinition:
        raise NotImplementedError

    async def list(
        self, *, workspace_id: UUID, status: str | None, limit: int, offset: int,
    ) -> tuple[list[SavedReportDefinition], int]:
        raise NotImplementedError

    async def get(self, *, workspace_id: UUID, saved_report_id: UUID) -> SavedReportDefinition | None:
        raise NotImplementedError

    async def update(
        self, *, workspace_id: UUID, saved_report_id: UUID, expected_version: int, changes: dict[str, Any],
    ) -> SavedReportDefinition:
        """Apply a partial update, enforcing optimistic concurrency.

        Raises ``SavedReportNotFoundError`` when no row in this workspace
        matches, or ``SavedReportVersionConflictError`` when ``expected_version``
        no longer matches the stored version -- a concurrent editor won the race.
        """

        raise NotImplementedError

    async def create_execution(
        self, *, workspace_id: UUID, saved_report_id: UUID, run_id: str, mode: str,
        resolved_period: tuple[date, date] | None, formats: list[str] | None,
        scheduled_report_id: UUID | None = None, retry_count: int = 0,
    ) -> SavedReportExecution:
        raise NotImplementedError

    async def finish_execution(
        self, *, workspace_id: UUID, run_id: str, status: str, error: str | None,
        error_category: str | None = None, usage_metadata: dict[str, Any] | None = None,
        artifact_ids: list[str] | None = None,
    ) -> None:
        """Verified through the execution's parent saved report, not by ``run_id`` alone."""

        raise NotImplementedError

    async def list_executions(
        self, *, workspace_id: UUID, saved_report_id: UUID, limit: int, offset: int,
    ) -> tuple[list[SavedReportExecution], int] | None:
        """Return ``None`` when the definition is not visible in this workspace."""

        raise NotImplementedError


class PostgresSavedReportStore(SavedReportStore):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def create(
        self, *, workspace_id: UUID, owner: str | None, name: str, description: str | None,
        template_id: str, template_version: str, metric_requests: list[SavedMetricRequest],
        default_period: RelativePeriod, narrative_policy: str,
        seed_run_id: str | None, seed_narrative: str | None, seed_narrative_period: str | None,
    ) -> SavedReportDefinition:
        stamp = _now()
        record = SavedReportRecord(
            id=uuid4(), workspace_id=workspace_id, owner=owner, name=name, description=description,
            template_id=template_id, template_version=template_version,
            metric_requests=[item.model_dump(mode="json") for item in metric_requests],
            default_period=default_period.model_dump(mode="json"),
            narrative_policy=narrative_policy,
            seed_run_id=seed_run_id, seed_narrative=seed_narrative, seed_narrative_period=seed_narrative_period,
            version=1, status="active", created_at=stamp, updated_at=stamp,
        )
        async with self._database.session() as session:
            async with session.begin():
                session.add(record)
        return _to_domain(record)

    async def list(
        self, *, workspace_id: UUID, status: str | None, limit: int, offset: int,
    ) -> tuple[list[SavedReportDefinition], int]:
        async with self._database.session() as session:
            query = select(SavedReportRecord).where(SavedReportRecord.workspace_id == workspace_id)
            count_query = select(func.count()).select_from(SavedReportRecord).where(
                SavedReportRecord.workspace_id == workspace_id
            )
            if status is not None:
                query = query.where(SavedReportRecord.status == status)
                count_query = count_query.where(SavedReportRecord.status == status)
            total = await session.scalar(count_query) or 0
            records = (await session.scalars(
                query.order_by(SavedReportRecord.updated_at.desc(), SavedReportRecord.id.desc())
                .limit(limit).offset(offset)
            )).all()
        return [_to_domain(record) for record in records], total

    async def get(self, *, workspace_id: UUID, saved_report_id: UUID) -> SavedReportDefinition | None:
        async with self._database.session() as session:
            record = await session.get(SavedReportRecord, saved_report_id)
        if record is None or record.workspace_id != workspace_id:
            return None
        return _to_domain(record)

    async def update(
        self, *, workspace_id: UUID, saved_report_id: UUID, expected_version: int, changes: dict[str, Any],
    ) -> SavedReportDefinition:
        async with self._database.session() as session:
            async with session.begin():
                record = await session.get(SavedReportRecord, saved_report_id)
                if record is None or record.workspace_id != workspace_id:
                    raise SavedReportNotFoundError(str(saved_report_id))
                if record.version != expected_version:
                    raise SavedReportVersionConflictError(expected=expected_version, actual=record.version)

                # Validate the *resulting* definition as a whole before writing
                # anything, so a partial, invalid update never reaches the row.
                # model_validate (not model_copy) so the cross-field validator
                # -- include_original needs a seed_narrative -- actually runs.
                merged = _to_domain(record).model_dump()
                merged.update(changes)
                candidate = SavedReportDefinition.model_validate(merged)
                for field in (
                    "name", "description", "template_id", "template_version", "metric_requests",
                    "default_period", "narrative_policy", "seed_run_id", "seed_narrative",
                    "seed_narrative_period", "status",
                ):
                    if field in changes:
                        value = getattr(candidate, field)
                        if field in {"metric_requests"}:
                            value = [item.model_dump(mode="json") for item in value]
                        elif field == "default_period":
                            value = value.model_dump(mode="json")
                        setattr(record, field, value)
                record.version += 1
                record.updated_at = _now()
        return _to_domain(record)

    async def create_execution(
        self, *, workspace_id: UUID, saved_report_id: UUID, run_id: str, mode: str,
        resolved_period: tuple[date, date] | None, formats: list[str] | None,
        scheduled_report_id: UUID | None = None, retry_count: int = 0,
    ) -> SavedReportExecution:
        async with self._database.session() as session:
            async with session.begin():
                parent = await session.get(SavedReportRecord, saved_report_id)
                if parent is None or parent.workspace_id != workspace_id:
                    raise SavedReportNotFoundError(str(saved_report_id))
                record = SavedReportExecutionRecord(
                    id=uuid4(), saved_report_id=saved_report_id, scheduled_report_id=scheduled_report_id,
                    run_id=run_id, mode=mode, status="running",
                    resolved_period_start=resolved_period[0] if resolved_period else None,
                    resolved_period_end=resolved_period[1] if resolved_period else None,
                    formats=formats, error=None, error_category=None, retry_count=retry_count,
                    usage_metadata=None, artifact_ids=None, created_at=_now(), completed_at=None,
                )
                session.add(record)
        return _execution_to_domain(record)

    async def finish_execution(
        self, *, workspace_id: UUID, run_id: str, status: str, error: str | None,
        error_category: str | None = None, usage_metadata: dict[str, Any] | None = None,
        artifact_ids: list[str] | None = None,
    ) -> None:
        async with self._database.session() as session:
            async with session.begin():
                record = await session.scalar(
                    select(SavedReportExecutionRecord)
                    .join(SavedReportRecord, SavedReportExecutionRecord.saved_report_id == SavedReportRecord.id)
                    .where(SavedReportExecutionRecord.run_id == run_id, SavedReportRecord.workspace_id == workspace_id)
                )
                if record is None:
                    return
                record.status, record.error, record.completed_at = status, error, _now()
                record.error_category = error_category
                if usage_metadata is not None:
                    record.usage_metadata = usage_metadata
                if artifact_ids is not None:
                    record.artifact_ids = artifact_ids

    async def list_executions(
        self, *, workspace_id: UUID, saved_report_id: UUID, limit: int, offset: int,
    ) -> tuple[list[SavedReportExecution], int] | None:
        async with self._database.session() as session:
            report = await session.get(SavedReportRecord, saved_report_id)
            if report is None or report.workspace_id != workspace_id:
                return None
            total = await session.scalar(
                select(func.count()).select_from(SavedReportExecutionRecord)
                .where(SavedReportExecutionRecord.saved_report_id == saved_report_id)
            ) or 0
            records = (await session.scalars(
                select(SavedReportExecutionRecord)
                .where(SavedReportExecutionRecord.saved_report_id == saved_report_id)
                .order_by(SavedReportExecutionRecord.created_at.desc(), SavedReportExecutionRecord.id.desc())
                .limit(limit).offset(offset)
            )).all()
        return [_execution_to_domain(record) for record in records], total
