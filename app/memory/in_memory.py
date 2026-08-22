"""Process-local implementation of the memory storage contract."""

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from app.memory.store import MemoryStore
from app.memory.records import Memory, MemoryType


class InMemoryMemoryStore(MemoryStore):
    """Concurrency-safe in-process store for development and tests."""

    def __init__(self) -> None:
        self._memories: dict[UUID, Memory] = {}
        self._lock = asyncio.Lock()

    async def create(self, memory: Memory) -> Memory:
        """Store a copy while retaining the caller-provided UUID."""

        async with self._lock:
            if memory.id in self._memories:
                raise ValueError(f"Memory already exists: {memory.id}")
            self._memories[memory.id] = memory.model_copy(deep=True)
            return memory.model_copy(deep=True)

    async def get(self, memory_id: UUID) -> Memory | None:
        """Retrieve an isolated copy of a memory."""

        async with self._lock:
            memory = self._memories.get(memory_id)
            return memory.model_copy(deep=True) if memory is not None else None

    async def list_memories(
        self,
        *,
        memory_type: MemoryType | None = None,
        run_id: str | None = None,
        session_id: str | None = None,
    ) -> list[Memory]:
        """List matching memories in creation order."""

        async with self._lock:
            return [
                memory.model_copy(deep=True)
                for memory in self._memories.values()
                if (memory_type is None or memory.memory_type is memory_type)
                and (run_id is None or memory.run_id == run_id)
                and (session_id is None or memory.session_id == session_id)
            ]

    async def update(self, memory: Memory) -> Memory | None:
        """Replace an existing memory, maintaining its original creation time."""

        async with self._lock:
            existing = self._memories.get(memory.id)
            if existing is None:
                return None
            updated = memory.model_copy(
                update={
                    "created_at": existing.created_at,
                    "updated_at": datetime.now(timezone.utc),
                },
                deep=True,
            )
            self._memories[memory.id] = updated
            return updated.model_copy(deep=True)

    async def delete(self, memory_id: UUID) -> bool:
        """Remove a memory by ID."""

        async with self._lock:
            return self._memories.pop(memory_id, None) is not None
