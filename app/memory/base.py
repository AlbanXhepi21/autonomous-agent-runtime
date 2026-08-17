"""Storage contract for the memory domain."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.memory.models import Memory, MemoryType


class MemoryStore(ABC):
    """Persist and retrieve memories without making domain or LLM decisions."""

    @abstractmethod
    async def create(self, memory: Memory) -> Memory:
        """Store a new memory and return the stored value."""

    @abstractmethod
    async def get(self, memory_id: UUID) -> Memory | None:
        """Return one memory by ID, if it exists."""

    @abstractmethod
    async def list_memories(
        self,
        *,
        memory_type: MemoryType | None = None,
        run_id: str | None = None,
        session_id: str | None = None,
    ) -> list[Memory]:
        """List memories matching the supplied storage filters."""

    @abstractmethod
    async def update(self, memory: Memory) -> Memory | None:
        """Replace an existing memory with its validated updated value."""

    @abstractmethod
    async def delete(self, memory_id: UUID) -> bool:
        """Delete one memory and report whether it existed."""
