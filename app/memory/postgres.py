"""PostgreSQL-backed implementation of the memory storage contract."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.records import MemoryRecord
from app.db.session import Database
from app.memory.store import MemoryStore
from app.memory.records import Memory, MemoryType


class PostgresMemoryStore(MemoryStore):
    """Store memories in PostgreSQL through an application-scoped async pool."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def create(self, memory: Memory) -> Memory:
        """Insert a memory while preserving its domain UUID and timestamps."""

        record = _record_from_memory(memory)
        try:
            async with self._database.session() as session:
                async with session.begin():
                    session.add(record)
                    await session.flush()
        except IntegrityError as error:
            raise ValueError(f"Memory already exists: {memory.id}") from error
        except SQLAlchemyError as error:
            raise RuntimeError("Memory storage operation failed") from error
        return _memory_from_record(record)

    async def get(self, memory_id: UUID) -> Memory | None:
        """Return one memory by UUID, if present."""

        try:
            async with self._database.session() as session:
                record = await session.get(MemoryRecord, memory_id)
                return _memory_from_record(record) if record is not None else None
        except SQLAlchemyError as error:
            raise RuntimeError("Memory storage operation failed") from error

    async def list_memories(
        self,
        *,
        memory_type: MemoryType | None = None,
        run_id: str | None = None,
        session_id: str | None = None,
    ) -> list[Memory]:
        """List matching records in stable creation order."""

        statement = select(MemoryRecord).order_by(
            MemoryRecord.created_at, MemoryRecord.id
        )
        if memory_type is not None:
            statement = statement.where(MemoryRecord.memory_type == memory_type.value)
        if run_id is not None:
            statement = statement.where(MemoryRecord.run_id == run_id)
        if session_id is not None:
            statement = statement.where(MemoryRecord.session_id == session_id)
        try:
            async with self._database.session() as session:
                records = (await session.scalars(statement)).all()
        except SQLAlchemyError as error:
            raise RuntimeError("Memory storage operation failed") from error
        return [_memory_from_record(record) for record in records]

    async def update(self, memory: Memory) -> Memory | None:
        """Replace mutable fields while preserving creation time and identity."""

        try:
            async with self._database.session() as session:
                async with session.begin():
                    record = await session.get(MemoryRecord, memory.id)
                    if record is None:
                        return None
                    record.memory_type = memory.memory_type.value
                    record.content = memory.content
                    record.metadata_ = dict(memory.metadata)
                    record.run_id = memory.run_id
                    record.session_id = memory.session_id
                    record.updated_at = datetime.now(timezone.utc)
                    await session.flush()
                    return _memory_from_record(record)
        except SQLAlchemyError as error:
            raise RuntimeError("Memory storage operation failed") from error

    async def delete(self, memory_id: UUID) -> bool:
        """Delete a record and report whether it existed."""

        try:
            async with self._database.session() as session:
                async with session.begin():
                    record = await session.get(MemoryRecord, memory_id)
                    if record is None:
                        return False
                    await session.delete(record)
                    return True
        except SQLAlchemyError as error:
            raise RuntimeError("Memory storage operation failed") from error

    async def close(self) -> None:
        """Dispose the shared database engine during application shutdown."""

        await self._database.dispose()


def _record_from_memory(memory: Memory) -> MemoryRecord:
    return MemoryRecord(
        id=memory.id,
        memory_type=memory.memory_type.value,
        content=memory.content,
        metadata_=dict(memory.metadata),
        run_id=memory.run_id,
        session_id=memory.session_id,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
    )


def _memory_from_record(record: MemoryRecord) -> Memory:
    return Memory(
        id=record.id,
        memory_type=MemoryType(record.memory_type),
        content=record.content,
        metadata=dict(record.metadata_),
        run_id=record.run_id,
        session_id=record.session_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
