"""Developer-only, sanitized inspection of intentionally retained V3 memories."""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import require_developer_mode
from app.composition import get_memory_store
from app.memory.records import Memory, MemoryType
from app.memory.store import MemoryStore
from app.security.credentials import contains_secret_material

router = APIRouter(prefix="/api/v1/memory", tags=["memory-inspector"])

def _safe(memory: Memory) -> dict[str, object]:
    if contains_secret_material(memory.content) or "chain-of-thought" in memory.content.lower() or "private reasoning" in memory.content.lower():
        raise HTTPException(status_code=404, detail={"code": "memory_unavailable", "message": "Memory is not available for inspection."})
    return {"id": str(memory.id), "type": memory.memory_type.value, "content": memory.content, "run_id": memory.run_id, "session_id": memory.session_id, "created_at": memory.created_at, "updated_at": memory.updated_at, "metadata": memory.metadata}

@router.get("")
async def list_memory(memory_type: MemoryType | None = None, run_id: str | None = None, session_id: str | None = None, created_after: datetime | None = Query(default=None), _: None = Depends(require_developer_mode), store: MemoryStore = Depends(get_memory_store)):
    memories = await store.list_memories(memory_type=memory_type, run_id=run_id, session_id=session_id)
    return [item for memory in memories if created_after is None or memory.created_at >= created_after for item in [_safe(memory)]]

@router.get("/{memory_id}")
async def get_memory(memory_id: UUID, _: None = Depends(require_developer_mode), store: MemoryStore = Depends(get_memory_store)):
    memory = await store.get(memory_id)
    if memory is None: raise HTTPException(status_code=404, detail={"code": "unknown_memory", "message": "Memory not found."})
    return _safe(memory)
