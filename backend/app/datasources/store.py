"""Persistence for workspace data sources and their governed catalog.

Follows the same shape as ``app.reports.store``: an abstract contract and one
PostgreSQL implementation, every workspace-scoped read and write filtered by
``workspace_id`` in the query itself -- a data source from another workspace
is treated exactly like one that does not exist. The encrypted password is
handled by exactly two methods (``create_connection``, ``get_encrypted_password``)
so every other method can be trusted never to touch it, structurally rather
than by convention.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from app.datasources.contracts import (
    ColumnRole,
    DataSourceColumnCatalogEntry,
    DataSourceConnection,
    DataSourceConnectionConfig,
    DataSourceRelationship,
    DataSourceStatus,
    DataSourceTableCatalogEntry,
    HealthStatus,
    RelationshipApprovalStatus,
    RelationshipCandidate,
    SensitivityClassification,
)
from app.db.records import (
    DataSourceColumnRecord,
    DataSourceRecord,
    DataSourceRelationshipRecord,
    DataSourceTableRecord,
)
from app.db.session import Database


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DataSourceNotFoundError(Exception):
    """Raised when a connection does not exist in the caller's workspace."""


class DataSourceTableNotFoundError(Exception):
    """Raised when a catalog table does not exist under the named connection."""


class DataSourceRelationshipNotFoundError(Exception):
    """Raised when a relationship does not exist under the named connection."""


def _connection_to_domain(record: DataSourceRecord) -> DataSourceConnection:
    return DataSourceConnection(
        id=record.id, workspace_id=record.workspace_id, name=record.name,
        config=DataSourceConnectionConfig(
            host=record.host, port=record.port, database=record.database_name, username=record.username,
            ssl_mode=record.ssl_mode, allowed_schemas=list(record.allowed_schemas),
            statement_timeout_seconds=record.statement_timeout_seconds,
            max_result_rows=record.max_result_rows, max_result_bytes=record.max_result_bytes,
        ),
        status=record.status, health_status=record.health_status,
        last_connection_at=record.last_connection_at, last_connection_error=record.last_connection_error,
        last_profiled_at=record.last_profiled_at, created_at=record.created_at, updated_at=record.updated_at,
    )


def _column_to_domain(record: DataSourceColumnRecord) -> DataSourceColumnCatalogEntry:
    return DataSourceColumnCatalogEntry(
        id=record.id, table_id=record.data_source_table_id, technical_name=record.technical_name,
        data_type=record.data_type, role=record.role, sensitivity=record.sensitivity,
        excluded=record.excluded, example_values=list(record.example_values or []),
    )


def _table_to_domain(record: DataSourceTableRecord, columns: list[DataSourceColumnRecord]) -> DataSourceTableCatalogEntry:
    return DataSourceTableCatalogEntry(
        id=record.id, data_source_id=record.data_source_id, schema_name=record.schema_name,
        technical_name=record.technical_name, business_name=record.business_name,
        description=record.description, grain=record.grain, freshness_column=record.freshness_column,
        active=record.active, approved_by=record.approved_by, approved_at=record.approved_at,
        columns=[_column_to_domain(column) for column in columns],
        created_at=record.created_at, updated_at=record.updated_at,
    )


def _relationship_to_domain(record: DataSourceRelationshipRecord) -> DataSourceRelationship:
    return DataSourceRelationship(
        id=record.id, data_source_id=record.data_source_id, source_table=record.source_table,
        source_column=record.source_column, target_table=record.target_table, target_column=record.target_column,
        cardinality=record.cardinality, confidence=record.confidence, discovery_method=record.discovery_method,
        approval_status=record.approval_status, approved_by=record.approved_by, approved_at=record.approved_at,
        created_at=record.created_at, updated_at=record.updated_at,
    )


class ColumnInput:
    """One column's classification, as supplied when a table is selected or corrected."""

    __slots__ = ("technical_name", "data_type", "role", "sensitivity", "excluded", "example_values")

    def __init__(
        self, *, technical_name: str, data_type: str, role: ColumnRole = "other",
        sensitivity: SensitivityClassification = "internal", excluded: bool = False,
        example_values: list[str] | None = None,
    ) -> None:
        self.technical_name = technical_name
        self.data_type = data_type
        self.role = role
        self.sensitivity = sensitivity
        self.excluded = excluded
        self.example_values = example_values or []


class DataSourceStore:
    """Persistence contract for connections and their governed catalog."""

    # -- connections -----------------------------------------------------

    async def create_connection(
        self, *, workspace_id: UUID, name: str, config: DataSourceConnectionConfig, encrypted_password: str,
    ) -> DataSourceConnection:
        raise NotImplementedError

    async def get_connection(self, *, workspace_id: UUID, data_source_id: UUID) -> DataSourceConnection | None:
        raise NotImplementedError

    async def get_encrypted_password(self, *, workspace_id: UUID, data_source_id: UUID) -> str | None:
        """The one method allowed to read ``encrypted_password`` back out.

        Returns ``None`` when the connection is not visible in this
        workspace -- indistinguishable from "does not exist," the same as
        every other workspace-scoped lookup here.
        """

        raise NotImplementedError

    async def list_connections(
        self, *, workspace_id: UUID, status: DataSourceStatus | None, limit: int, offset: int,
    ) -> tuple[list[DataSourceConnection], int]:
        raise NotImplementedError

    async def update_connection_status(
        self, *, workspace_id: UUID, data_source_id: UUID, status: DataSourceStatus | None = None,
        health_status: HealthStatus | None = None, last_connection_at: datetime | None = None,
        last_connection_error: str | None = None, last_profiled_at: datetime | None = None,
    ) -> DataSourceConnection:
        raise NotImplementedError

    async def update_connection_config(
        self, *, workspace_id: UUID, data_source_id: UUID, changes: dict[str, Any],
    ) -> DataSourceConnection:
        raise NotImplementedError

    # -- catalog: tables and columns --------------------------------------

    async def upsert_table(
        self, *, workspace_id: UUID, data_source_id: UUID, schema_name: str, technical_name: str,
        business_name: str, description: str | None, grain: str | None, freshness_column: str | None,
        columns: list[ColumnInput],
    ) -> DataSourceTableCatalogEntry:
        """Create or replace one table's catalog entry, including its columns.

        A second call for the same (schema, technical_name) replaces the
        table-level fields and re-derives its columns from ``columns`` --
        the correction step of onboarding ("let an authorized user approve
        or correct metadata") is this same operation, not a separate one.
        """

        raise NotImplementedError

    async def get_table(self, *, workspace_id: UUID, data_source_id: UUID, table_id: UUID) -> DataSourceTableCatalogEntry | None:
        raise NotImplementedError

    async def list_tables(
        self, *, workspace_id: UUID, data_source_id: UUID, active_only: bool = False,
    ) -> list[DataSourceTableCatalogEntry] | None:
        """Return ``None`` when the connection itself is not visible here."""

        raise NotImplementedError

    async def set_table_active(
        self, *, workspace_id: UUID, data_source_id: UUID, table_id: UUID, active: bool,
    ) -> DataSourceTableCatalogEntry:
        raise NotImplementedError

    async def approve_table(
        self, *, workspace_id: UUID, data_source_id: UUID, table_id: UUID, approved_by: str,
    ) -> DataSourceTableCatalogEntry:
        raise NotImplementedError

    # -- catalog: relationships --------------------------------------------

    async def create_relationship_candidates(
        self, *, workspace_id: UUID, data_source_id: UUID, candidates: list[RelationshipCandidate],
    ) -> list[DataSourceRelationship]:
        raise NotImplementedError

    async def list_relationships(
        self, *, workspace_id: UUID, data_source_id: UUID, approval_status: RelationshipApprovalStatus | None = None,
    ) -> list[DataSourceRelationship] | None:
        """Return ``None`` when the connection itself is not visible here."""

        raise NotImplementedError

    async def set_relationship_approval(
        self, *, workspace_id: UUID, data_source_id: UUID, relationship_id: UUID,
        approval_status: RelationshipApprovalStatus, approved_by: str | None,
    ) -> DataSourceRelationship:
        raise NotImplementedError


class PostgresDataSourceStore(DataSourceStore):
    def __init__(self, database: Database) -> None:
        self._database = database

    # -- connections -----------------------------------------------------

    async def create_connection(
        self, *, workspace_id: UUID, name: str, config: DataSourceConnectionConfig, encrypted_password: str,
    ) -> DataSourceConnection:
        stamp = _now()
        record = DataSourceRecord(
            id=uuid4(), workspace_id=workspace_id, name=name, host=config.host, port=config.port,
            database_name=config.database, username=config.username, encrypted_password=encrypted_password,
            ssl_mode=config.ssl_mode, allowed_schemas=list(config.allowed_schemas),
            statement_timeout_seconds=config.statement_timeout_seconds, max_result_rows=config.max_result_rows,
            max_result_bytes=config.max_result_bytes, status="pending", health_status="unknown",
            last_connection_at=None, last_connection_error=None, last_profiled_at=None,
            created_at=stamp, updated_at=stamp,
        )
        async with self._database.session() as session:
            async with session.begin():
                session.add(record)
        return _connection_to_domain(record)

    async def get_connection(self, *, workspace_id: UUID, data_source_id: UUID) -> DataSourceConnection | None:
        async with self._database.session() as session:
            record = await session.get(DataSourceRecord, data_source_id)
        if record is None or record.workspace_id != workspace_id:
            return None
        return _connection_to_domain(record)

    async def get_encrypted_password(self, *, workspace_id: UUID, data_source_id: UUID) -> str | None:
        async with self._database.session() as session:
            record = await session.get(DataSourceRecord, data_source_id)
        if record is None or record.workspace_id != workspace_id:
            return None
        return record.encrypted_password

    async def list_connections(
        self, *, workspace_id: UUID, status: DataSourceStatus | None, limit: int, offset: int,
    ) -> tuple[list[DataSourceConnection], int]:
        async with self._database.session() as session:
            query = select(DataSourceRecord).where(DataSourceRecord.workspace_id == workspace_id)
            if status is not None:
                query = query.where(DataSourceRecord.status == status)
            total = len((await session.scalars(query)).all())
            records = (await session.scalars(
                query.order_by(DataSourceRecord.updated_at.desc()).limit(limit).offset(offset)
            )).all()
        return [_connection_to_domain(record) for record in records], total

    async def update_connection_status(
        self, *, workspace_id: UUID, data_source_id: UUID, status: DataSourceStatus | None = None,
        health_status: HealthStatus | None = None, last_connection_at: datetime | None = None,
        last_connection_error: str | None = None, last_profiled_at: datetime | None = None,
    ) -> DataSourceConnection:
        async with self._database.session() as session:
            async with session.begin():
                record = await session.get(DataSourceRecord, data_source_id)
                if record is None or record.workspace_id != workspace_id:
                    raise DataSourceNotFoundError(str(data_source_id))
                if status is not None:
                    record.status = status
                if health_status is not None:
                    record.health_status = health_status
                if last_connection_at is not None:
                    record.last_connection_at = last_connection_at
                    record.last_connection_error = last_connection_error
                if last_profiled_at is not None:
                    record.last_profiled_at = last_profiled_at
                record.updated_at = _now()
        return _connection_to_domain(record)

    async def update_connection_config(
        self, *, workspace_id: UUID, data_source_id: UUID, changes: dict[str, Any],
    ) -> DataSourceConnection:
        async with self._database.session() as session:
            async with session.begin():
                record = await session.get(DataSourceRecord, data_source_id)
                if record is None or record.workspace_id != workspace_id:
                    raise DataSourceNotFoundError(str(data_source_id))
                if "name" in changes:
                    record.name = changes["name"]
                config: DataSourceConnectionConfig | None = changes.get("config")
                if config is not None:
                    record.host, record.port = config.host, config.port
                    record.database_name, record.username = config.database, config.username
                    record.ssl_mode = config.ssl_mode
                    record.allowed_schemas = list(config.allowed_schemas)
                    record.statement_timeout_seconds = config.statement_timeout_seconds
                    record.max_result_rows, record.max_result_bytes = config.max_result_rows, config.max_result_bytes
                    # A connection detail changed -- whatever this connection
                    # last proved about itself no longer applies.
                    record.status = "pending"
                if "encrypted_password" in changes:
                    record.encrypted_password = changes["encrypted_password"]
                    record.status = "pending"
                record.updated_at = _now()
        return _connection_to_domain(record)

    # -- catalog: tables and columns --------------------------------------

    async def upsert_table(
        self, *, workspace_id: UUID, data_source_id: UUID, schema_name: str, technical_name: str,
        business_name: str, description: str | None, grain: str | None, freshness_column: str | None,
        columns: list[ColumnInput],
    ) -> DataSourceTableCatalogEntry:
        async with self._database.session() as session:
            async with session.begin():
                source = await session.get(DataSourceRecord, data_source_id)
                if source is None or source.workspace_id != workspace_id:
                    raise DataSourceNotFoundError(str(data_source_id))

                existing = await session.scalar(
                    select(DataSourceTableRecord)
                    .where(DataSourceTableRecord.data_source_id == data_source_id)
                    .where(DataSourceTableRecord.schema_name == schema_name)
                    .where(DataSourceTableRecord.technical_name == technical_name)
                )
                stamp = _now()
                if existing is None:
                    table = DataSourceTableRecord(
                        id=uuid4(), data_source_id=data_source_id, schema_name=schema_name,
                        technical_name=technical_name, business_name=business_name, description=description,
                        grain=grain, freshness_column=freshness_column, active=True,
                        approved_by=None, approved_at=None, created_at=stamp, updated_at=stamp,
                    )
                    session.add(table)
                    await session.flush()
                else:
                    table = existing
                    table.business_name, table.description = business_name, description
                    table.grain, table.freshness_column = grain, freshness_column
                    # A correction resets approval -- new metadata has not
                    # itself been reviewed yet, even if the table shape hasn't changed.
                    table.approved_by, table.approved_at = None, None
                    table.updated_at = stamp
                    await session.execute(
                        DataSourceColumnRecord.__table__.delete()
                        .where(DataSourceColumnRecord.data_source_table_id == table.id)
                    )

                column_records = [
                    DataSourceColumnRecord(
                        id=uuid4(), data_source_table_id=table.id, technical_name=column.technical_name,
                        data_type=column.data_type, role=column.role, sensitivity=column.sensitivity,
                        excluded=column.excluded, example_values=list(column.example_values) or None,
                        created_at=stamp, updated_at=stamp,
                    )
                    for column in columns
                ]
                session.add_all(column_records)
        return _table_to_domain(table, column_records)

    async def get_table(
        self, *, workspace_id: UUID, data_source_id: UUID, table_id: UUID,
    ) -> DataSourceTableCatalogEntry | None:
        async with self._database.session() as session:
            source = await session.get(DataSourceRecord, data_source_id)
            if source is None or source.workspace_id != workspace_id:
                return None
            table = await session.get(DataSourceTableRecord, table_id)
            if table is None or table.data_source_id != data_source_id:
                return None
            columns = (await session.scalars(
                select(DataSourceColumnRecord).where(DataSourceColumnRecord.data_source_table_id == table_id)
            )).all()
        return _table_to_domain(table, list(columns))

    async def list_tables(
        self, *, workspace_id: UUID, data_source_id: UUID, active_only: bool = False,
    ) -> list[DataSourceTableCatalogEntry] | None:
        async with self._database.session() as session:
            source = await session.get(DataSourceRecord, data_source_id)
            if source is None or source.workspace_id != workspace_id:
                return None
            query = select(DataSourceTableRecord).where(DataSourceTableRecord.data_source_id == data_source_id)
            if active_only:
                query = query.where(DataSourceTableRecord.active.is_(True))
            tables = (await session.scalars(query.order_by(DataSourceTableRecord.technical_name))).all()
            entries = []
            for table in tables:
                columns = (await session.scalars(
                    select(DataSourceColumnRecord).where(DataSourceColumnRecord.data_source_table_id == table.id)
                )).all()
                entries.append(_table_to_domain(table, list(columns)))
        return entries

    async def set_table_active(
        self, *, workspace_id: UUID, data_source_id: UUID, table_id: UUID, active: bool,
    ) -> DataSourceTableCatalogEntry:
        async with self._database.session() as session:
            async with session.begin():
                source = await session.get(DataSourceRecord, data_source_id)
                if source is None or source.workspace_id != workspace_id:
                    raise DataSourceNotFoundError(str(data_source_id))
                table = await session.get(DataSourceTableRecord, table_id)
                if table is None or table.data_source_id != data_source_id:
                    raise DataSourceTableNotFoundError(str(table_id))
                table.active, table.updated_at = active, _now()
                columns = (await session.scalars(
                    select(DataSourceColumnRecord).where(DataSourceColumnRecord.data_source_table_id == table_id)
                )).all()
        return _table_to_domain(table, list(columns))

    async def approve_table(
        self, *, workspace_id: UUID, data_source_id: UUID, table_id: UUID, approved_by: str,
    ) -> DataSourceTableCatalogEntry:
        async with self._database.session() as session:
            async with session.begin():
                source = await session.get(DataSourceRecord, data_source_id)
                if source is None or source.workspace_id != workspace_id:
                    raise DataSourceNotFoundError(str(data_source_id))
                table = await session.get(DataSourceTableRecord, table_id)
                if table is None or table.data_source_id != data_source_id:
                    raise DataSourceTableNotFoundError(str(table_id))
                stamp = _now()
                table.approved_by, table.approved_at, table.updated_at = approved_by, stamp, stamp
                columns = (await session.scalars(
                    select(DataSourceColumnRecord).where(DataSourceColumnRecord.data_source_table_id == table_id)
                )).all()
        return _table_to_domain(table, list(columns))

    # -- catalog: relationships --------------------------------------------

    async def create_relationship_candidates(
        self, *, workspace_id: UUID, data_source_id: UUID, candidates: list[RelationshipCandidate],
    ) -> list[DataSourceRelationship]:
        async with self._database.session() as session:
            async with session.begin():
                source = await session.get(DataSourceRecord, data_source_id)
                if source is None or source.workspace_id != workspace_id:
                    raise DataSourceNotFoundError(str(data_source_id))
                stamp = _now()
                records = [
                    DataSourceRelationshipRecord(
                        id=uuid4(), data_source_id=data_source_id, source_table=candidate.source_table,
                        source_column=candidate.source_column, target_table=candidate.target_table,
                        target_column=candidate.target_column, cardinality=candidate.cardinality,
                        confidence=candidate.confidence, discovery_method=candidate.discovery_method,
                        # A foreign-key-derived candidate is unambiguous enough that a
                        # reviewer confirming it is a formality, not a judgement call --
                        # still not "trusted" for querying until approved, but it is a
                        # smaller ask than reviewing an inferred, heuristic candidate.
                        approval_status="pending", approved_by=None, approved_at=None,
                        created_at=stamp, updated_at=stamp,
                    )
                    for candidate in candidates
                ]
                session.add_all(records)
        return [_relationship_to_domain(record) for record in records]

    async def list_relationships(
        self, *, workspace_id: UUID, data_source_id: UUID, approval_status: RelationshipApprovalStatus | None = None,
    ) -> list[DataSourceRelationship] | None:
        async with self._database.session() as session:
            source = await session.get(DataSourceRecord, data_source_id)
            if source is None or source.workspace_id != workspace_id:
                return None
            query = select(DataSourceRelationshipRecord).where(
                DataSourceRelationshipRecord.data_source_id == data_source_id
            )
            if approval_status is not None:
                query = query.where(DataSourceRelationshipRecord.approval_status == approval_status)
            records = (await session.scalars(query.order_by(DataSourceRelationshipRecord.confidence.desc()))).all()
        return [_relationship_to_domain(record) for record in records]

    async def set_relationship_approval(
        self, *, workspace_id: UUID, data_source_id: UUID, relationship_id: UUID,
        approval_status: RelationshipApprovalStatus, approved_by: str | None,
    ) -> DataSourceRelationship:
        async with self._database.session() as session:
            async with session.begin():
                source = await session.get(DataSourceRecord, data_source_id)
                if source is None or source.workspace_id != workspace_id:
                    raise DataSourceNotFoundError(str(data_source_id))
                record = await session.get(DataSourceRelationshipRecord, relationship_id)
                if record is None or record.data_source_id != data_source_id:
                    raise DataSourceRelationshipNotFoundError(str(relationship_id))
                stamp = _now()
                record.approval_status = approval_status
                record.approved_by = approved_by if approval_status == "approved" else None
                record.approved_at = stamp if approval_status == "approved" else None
                record.updated_at = stamp
        return _relationship_to_domain(record)
