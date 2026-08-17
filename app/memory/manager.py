"""Domain-oriented operations over a memory store."""

import logging
from typing import Any
from uuid import UUID

from app.core.logging import log_event, safe_log_value
from app.memory.base import MemoryStore
from app.memory.models import Memory, MemoryType


class MemoryManager:
    """Create and organize memories while keeping storage implementation hidden."""

    def __init__(self, store: MemoryStore) -> None:
        self._store = store
        self._logger = logging.getLogger(__name__)

    async def add_working_memory(
        self, content: str, *, run_id: str, session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Memory:
        """Record information needed during the current run."""

        return await self._add(
            MemoryType.WORKING, content, run_id=run_id, session_id=session_id, metadata=metadata
        )

    async def add_episodic_memory(
        self, content: str, *, run_id: str | None = None, session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Memory:
        """Record a useful previous-run experience."""

        return await self._add(
            MemoryType.EPISODIC, content, run_id=run_id, session_id=session_id, metadata=metadata
        )

    async def add_long_term_memory(
        self, content: str, *, session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Memory:
        """Record durable future-useful context."""

        return await self._add(
            MemoryType.LONG_TERM, content, session_id=session_id, metadata=metadata
        )

    async def get_memories(
        self, memory_type: MemoryType, *, run_id: str | None = None,
        session_id: str | None = None,
    ) -> list[Memory]:
        """Retrieve memories of one domain type without ranking them."""

        return await self._store.list_memories(
            memory_type=memory_type, run_id=run_id, session_id=session_id
        )

    async def update_memory(self, memory: Memory) -> Memory | None:
        """Persist a validated memory update and record its lifecycle event."""

        updated = await self._store.update(memory)
        if updated is not None:
            self._log("memory_updated", updated)
        return updated

    async def delete_memory(self, memory_id: UUID) -> bool:
        """Delete a memory while retaining enough context for safe logging."""

        memory = await self._store.get(memory_id)
        deleted = await self._store.delete(memory_id)
        if deleted and memory is not None:
            self._log("memory_deleted", memory)
        return deleted

    async def clear_working_memory(self, run_id: str) -> int:
        """Remove working memories belonging to one completed run."""

        memories = await self.get_memories(MemoryType.WORKING, run_id=run_id)
        deleted = 0
        for memory in memories:
            if await self.delete_memory(memory.id):
                deleted += 1
        log_event(
            self._logger,
            logging.INFO,
            "working_memory_cleared",
            run_id=run_id,
            memory_type=MemoryType.WORKING,
            deleted_count=deleted,
        )
        return deleted

    async def _add(
        self, memory_type: MemoryType, content: str, *, run_id: str | None = None,
        session_id: str | None = None, metadata: dict[str, Any] | None = None,
    ) -> Memory:
        memory = await self._store.create(
            Memory(
                memory_type=memory_type,
                content=content,
                run_id=run_id,
                session_id=session_id,
                metadata=metadata or {},
            )
        )
        self._log("memory_created", memory)
        return memory

    def _log(self, event: str, memory: Memory) -> None:
        log_event(
            self._logger,
            logging.INFO,
            event,
            run_id=memory.run_id,
            memory_id=str(memory.id),
            memory_type=memory.memory_type,
            session_id=memory.session_id,
            metadata=safe_log_value(memory.metadata),
        )
