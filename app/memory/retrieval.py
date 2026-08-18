"""Deterministic selection of historical memories for an agent goal."""

import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.memory.base import MemoryStore
from app.memory.models import Memory, MemoryType

MAX_RETRIEVED_MEMORIES = 5
_TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")
_STOP_WORDS = frozenset({"a", "an", "and", "for", "from", "how", "in", "is", "of", "on", "the", "to", "with"})
_TYPE_WEIGHT = {MemoryType.LONG_TERM: 3, MemoryType.EPISODIC: 2, MemoryType.WORKING: 1}


class MemoryRetrievalRequest(BaseModel):
    """Constraints for selecting a small, explainable set of memories."""

    query: str = Field(min_length=1)
    memory_types: tuple[MemoryType, ...] = (MemoryType.EPISODIC, MemoryType.LONG_TERM)
    session_id: str | None = None
    limit: int = Field(default=MAX_RETRIEVED_MEMORIES, ge=1, le=MAX_RETRIEVED_MEMORIES)
    created_after: datetime | None = None
    tags: tuple[str, ...] = ()
    metadata_filters: dict[str, Any] = Field(default_factory=dict)


class MemoryRetrievalResult(BaseModel):
    """The selected memories plus a count useful for safe operational logging."""

    memories: list[Memory]
    candidate_count: int


class MemoryRetriever:
    """Rank storage candidates without adding relevance decisions to a store."""

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    async def retrieve(self, request: MemoryRetrievalRequest) -> MemoryRetrievalResult:
        """Fetch basic-filtered candidates, then rank them deterministically in memory."""

        candidates = await self._candidates(request)
        query_tokens = _tokens(request.query)
        ranked: list[tuple[int, Memory]] = []
        for memory in candidates:
            metadata_tokens = _tokens(_metadata_text(memory.metadata))
            overlap = len(query_tokens & (_tokens(memory.content) | metadata_tokens))
            tag_matches = len({tag.lower() for tag in request.tags} & _tags(memory.metadata))
            # With a meaningful query, exclude records with no lexical or explicit tag match.
            if query_tokens and overlap == 0 and tag_matches == 0:
                continue
            ranked.append((overlap * 100 + tag_matches * 25 + _TYPE_WEIGHT[memory.memory_type], memory))

        # Recency is a small tie-breaker.  It is derived from stored timestamps, not wall clock time.
        by_recency = sorted(ranked, key=lambda item: (item[1].created_at, str(item[1].id)), reverse=True)
        recency_bonus = {memory.id: len(by_recency) - index for index, (_, memory) in enumerate(by_recency)}
        selected = sorted(
            ranked,
            key=lambda item: (-item[0] - recency_bonus[item[1].id], -item[1].created_at.timestamp(), str(item[1].id)),
        )[: request.limit]
        return MemoryRetrievalResult(
            memories=[memory for _, memory in selected], candidate_count=len(candidates)
        )

    async def _candidates(self, request: MemoryRetrievalRequest) -> list[Memory]:
        memories: list[Memory] = []
        for memory_type in request.memory_types:
            # Fetching the basic type candidate set lets the retriever include global
            # records for a session while excluding records from every other session.
            memories.extend(await self._store.list_memories(memory_type=memory_type))
        return [
            memory
            for memory in memories
            if memory.session_id in ({None} if request.session_id is None else {None, request.session_id})
            and (request.created_after is None or memory.created_at >= request.created_after)
            and all(memory.metadata.get(key) == value for key, value in request.metadata_filters.items())
        ]


def _tokens(value: str) -> set[str]:
    return {token for token in _TOKEN_PATTERN.findall(value.lower()) if token not in _STOP_WORDS}


def _tags(metadata: dict[str, Any]) -> set[str]:
    value = metadata.get("tags", ())
    if isinstance(value, str):
        return {value.lower()}
    if isinstance(value, Iterable) and not isinstance(value, dict):
        return {str(item).lower() for item in value}
    return set()


def _metadata_text(metadata: dict[str, Any]) -> str:
    return " ".join([str(value) for key, value in metadata.items() if key != "tags"] + list(_tags(metadata)))
