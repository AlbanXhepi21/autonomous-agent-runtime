"""Storage contract for the memory domain.

``list_memories`` requires ``workspace_id`` -- unlike ``run_id``/``session_id``,
which are optional narrowing filters, this one is never optional. Retrieval
candidates are otherwise selected by type alone (see
``app.memory.retrieval.MemoryRetriever``, which reads across every session
for long-term/episodic recall); without a mandatory workspace filter that
scan would cross tenants.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.memory.records import Memory, MemoryType


class MemoryStore(ABC):
    """Persist and retrieve memories without making domain or LLM decisions."""

    @abstractmethod
    async def create(self, memory: Memory) -> Memory:
        """Store a new memory and return the stored value. ``memory.workspace_id`` is required."""

    @abstractmethod
    async def get(self, *, workspace_id: UUID, memory_id: UUID) -> Memory | None:
        """Return one memory by ID, if it exists in this workspace."""

    @abstractmethod
    async def list_memories(
        self,
        *,
        workspace_id: UUID,
        memory_type: MemoryType | None = None,
        run_id: str | None = None,
        session_id: str | None = None,
    ) -> list[Memory]:
        """List memories matching the supplied storage filters, within one workspace."""

    @abstractmethod
    async def update(self, memory: Memory) -> Memory | None:
        """Replace an existing memory, verified against ``memory.workspace_id``."""

    @abstractmethod
    async def delete(self, *, workspace_id: UUID, memory_id: UUID) -> bool:
        """Delete one memory and report whether it existed in this workspace."""
