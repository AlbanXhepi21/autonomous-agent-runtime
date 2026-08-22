"""Curated, policy-gated writing of future-useful agent memory."""

import logging
import re
from collections.abc import Sequence
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.contracts.runs import CompletedRun
from app.core.logging import log_event, safe_error_message
from app.memory.manager import MemoryManager
from app.memory.models import MemoryType
from app.security.credentials import contains_secret_material


class MemoryCategory(StrEnum):
    """Small set of durable knowledge categories, not execution-history labels."""

    STABLE_FACT = "stable_fact"
    PROJECT_CONTEXT = "project_context"
    DECISION = "decision"
    PREFERENCE = "preference"
    RESOLVED_ISSUE = "resolved_issue"
    LESSON = "lesson"


class MemoryCandidate(BaseModel):
    """A proposal that must pass runtime policy before it can be persisted."""

    content: str = Field(min_length=1)
    memory_type: MemoryType
    category: MemoryCategory
    reason: str = Field(min_length=1)
    confidence: float = Field(default=1.0, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_run_id: str


class MemoryCandidateExtractor(Protocol):
    """Propose candidates only; implementations have no access to storage."""

    async def extract(self, state: CompletedRun) -> Sequence[MemoryCandidate]:
        """Return potential future-useful memories from a completed run."""


class DeterministicMemoryCandidateExtractor:
    """Extract only explicit task-summary decisions and clear durable outcomes."""

    async def extract(self, state: CompletedRun) -> Sequence[MemoryCandidate]:
        if not state.completed:
            return []
        candidates: list[MemoryCandidate] = []
        if state.task_summary is not None:
            candidates.extend(
                MemoryCandidate(
                    content=decision,
                    memory_type=MemoryType.LONG_TERM,
                    category=MemoryCategory.DECISION,
                    reason="Explicit decision recorded in the task summary.",
                    source_run_id=state.run_id,
                )
                for decision in state.task_summary.important_decisions
                if decision.strip()
            )
        if state.final_answer and _is_durable_outcome(state.final_answer):
            candidates.append(
                MemoryCandidate(
                    content=state.final_answer,
                    memory_type=MemoryType.EPISODIC,
                    category=MemoryCategory.RESOLVED_ISSUE,
                    reason="Completed run reported a reusable resolved outcome.",
                    source_run_id=state.run_id,
                )
            )
        return candidates


class MemoryPolicy:
    """Deterministic eligibility rules that reject execution traces and weak prose."""

    _REJECTED_PATTERNS = re.compile(
        r"\b(iteration|tool (?:succeeded|success|failed)|duplicate|calculation|temporary|"
        r"transient|retry|status|error occurred)\b",
        re.IGNORECASE,
    )
    _GENERIC_PROSE = re.compile(r"^(?:i |here(?:'s| is) |the task |done[.!]?$)", re.IGNORECASE)
    _PRIVATE_METADATA = frozenset({"reasoning", "chain_of_thought", "private_reasoning"})
    _LONG_TERM_CATEGORIES = frozenset({
        MemoryCategory.STABLE_FACT, MemoryCategory.PROJECT_CONTEXT, MemoryCategory.DECISION,
        MemoryCategory.PREFERENCE, MemoryCategory.RESOLVED_ISSUE, MemoryCategory.LESSON,
    })

    def rejection_reason(self, candidate: MemoryCandidate) -> str | None:
        content = candidate.content.strip()
        if contains_secret_material(content):
            return "credential_material"
        if candidate.memory_type is MemoryType.WORKING:
            return "working_memory_is_not_durable"
        if len(content) < 20:
            return "content_too_short"
        if candidate.confidence < 0.6:
            return "confidence_too_low"
        if self._PRIVATE_METADATA & set(candidate.metadata):
            return "private_reasoning_metadata"
        if re.search(r"\b(chain[ -]?of[ -]?thought|private reasoning)\b", content, re.IGNORECASE):
            return "private_reasoning_content"
        if self._REJECTED_PATTERNS.search(content):
            return "transient_execution_history"
        if self._GENERIC_PROSE.search(content):
            return "generic_assistant_prose"
        if candidate.memory_type is MemoryType.LONG_TERM and candidate.category not in self._LONG_TERM_CATEGORIES:
            return "unsupported_long_term_category"
        return None


class MemoryWritingPipeline:
    """Own candidate validation, duplicate checks, and persistence after completion."""

    def __init__(
        self, manager: MemoryManager, *, extractor: MemoryCandidateExtractor | None = None,
        policy: MemoryPolicy | None = None,
    ) -> None:
        self._manager = manager
        self._extractor = extractor or DeterministicMemoryCandidateExtractor()
        self._policy = policy or MemoryPolicy()
        self._logger = logging.getLogger(__name__)

    async def capture_completed_run(self, state: CompletedRun, *, session_id: str | None = None) -> None:
        """Best-effort curation; failure must never change a completed run result."""

        if not state.completed:
            return
        try:
            candidates = await self._extractor.extract(state)
        except Exception as error:
            log_event(
                self._logger, logging.WARNING, "memory_candidate_rejected", run_id=state.run_id,
                reason="extraction_failed", error_type=type(error).__name__, error=safe_error_message(error),
            )
            return
        for candidate in candidates:
            if candidate.source_run_id != state.run_id:
                log_event(
                    self._logger, logging.WARNING, "memory_candidate_rejected", run_id=state.run_id,
                    reason="source_run_mismatch", category=candidate.category,
                )
                continue
            try:
                await self._consider(candidate, session_id=session_id)
            except Exception as error:
                log_event(
                    self._logger, logging.WARNING, "memory_candidate_rejected", run_id=candidate.source_run_id,
                    reason="persistence_failed", error_type=type(error).__name__, error=safe_error_message(error),
                )

    async def _consider(self, candidate: MemoryCandidate, *, session_id: str | None) -> None:
        log_event(
            self._logger, logging.INFO, "memory_candidate_created", run_id=candidate.source_run_id,
            memory_type=candidate.memory_type, category=candidate.category, confidence=candidate.confidence,
        )
        if reason := self._policy.rejection_reason(candidate):
            log_event(
                self._logger, logging.INFO, "memory_candidate_rejected", run_id=candidate.source_run_id,
                memory_type=candidate.memory_type, category=candidate.category, reason=reason,
            )
            return
        if await self._is_duplicate(candidate):
            log_event(
                self._logger, logging.INFO, "memory_duplicate_skipped", run_id=candidate.source_run_id,
                memory_type=candidate.memory_type, category=candidate.category,
            )
            return
        log_event(
            self._logger, logging.INFO, "memory_candidate_accepted", run_id=candidate.source_run_id,
            memory_type=candidate.memory_type, category=candidate.category,
        )
        # Candidate rationale is deliberately not persisted: it may be internal or non-durable.
        metadata = {**candidate.metadata, "category": candidate.category}
        if candidate.memory_type is MemoryType.EPISODIC:
            memory = await self._manager.add_episodic_memory(
                candidate.content, run_id=candidate.source_run_id, session_id=session_id, metadata=metadata,
            )
        else:
            memory = await self._manager.add_long_term_memory(
                candidate.content, session_id=session_id, metadata=metadata,
            )
        log_event(
            self._logger, logging.INFO, "memory_persisted", run_id=candidate.source_run_id,
            memory_id=str(memory.id), memory_type=memory.memory_type, category=candidate.category,
        )

    async def _is_duplicate(self, candidate: MemoryCandidate) -> bool:
        normalized = _normalize(candidate.content)
        memories = await self._manager.get_memories(candidate.memory_type)
        return any(_normalize(memory.content) == normalized for memory in memories)


def _is_durable_outcome(content: str) -> bool:
    return bool(re.search(r"\b(resolved|fixed|implemented|decided|learned)\b", content, re.IGNORECASE))


def _normalize(content: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", content.lower()))
