import pytest
from fastapi import HTTPException

from app.api.routes.memory import _safe
from app.memory.records import Memory, MemoryType


def test_memory_inspector_exposes_actual_provenance() -> None:
    memory = Memory(memory_type=MemoryType.LONG_TERM, content="User prefers quarterly comparisons.", run_id="run-1", metadata={"category": "preference"})
    response = _safe(memory)
    assert response["type"] == "long_term" and response["run_id"] == "run-1"


def test_memory_inspector_hides_secret_or_private_reasoning() -> None:
    with pytest.raises(HTTPException): _safe(Memory(memory_type=MemoryType.EPISODIC, content="token=sk-secret-value"))
    with pytest.raises(HTTPException): _safe(Memory(memory_type=MemoryType.EPISODIC, content="Private reasoning content must not show."))
