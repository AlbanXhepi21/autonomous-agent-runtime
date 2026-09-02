"""Expire artifacts: delete the bytes, keep the row as an audit trail.

Never a hard delete: a claimed, expired artifact keeps its full metadata row
after its bytes are gone -- only ``status`` moves to ``DELETED`` and
``deleted_at`` is stamped. A ``legal_hold`` or ``permanent`` artifact is never
claimed regardless of ``expires_at``, enforced by the store's own claim query
rather than a check here, so a caller cannot bypass it by calling the worker
directly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from app.artifacts.contracts import Artifact
from app.artifacts.files import WorkspaceArtifactFiles
from app.artifacts.store import ArtifactStore
from app.core.logging import log_event, safe_error_message

_logger = logging.getLogger(__name__)

RetentionOutcomeStatus = Literal["deleted", "failed", "gave_up"]


@dataclass(frozen=True, slots=True)
class RetentionOutcome:
    """What one claimed artifact's deletion attempt produced."""

    artifact_id: str
    status: RetentionOutcomeStatus
    error: str | None


class RetentionWorker:
    """Claim expired artifacts and delete their bytes, a batch at a time."""

    def __init__(
        self, *, artifacts: ArtifactStore, files: WorkspaceArtifactFiles,
        max_attempts: int = 5, stale_claim_after: timedelta = timedelta(minutes=15),
    ) -> None:
        self._artifacts = artifacts
        self._files = files
        self._max_attempts = max_attempts
        self._stale_claim_after = stale_claim_after

    async def run_once(self, *, batch_size: int = 50, now: datetime | None = None) -> list[RetentionOutcome]:
        """Claim and process every currently-expired artifact, up to ``batch_size``."""

        reference = now or datetime.now(timezone.utc)
        claimed = await self._artifacts.claim_expired(
            now=reference, stale_after=self._stale_claim_after, limit=batch_size,
            max_attempts=self._max_attempts,
        )
        return [await self._delete_one(artifact) for artifact in claimed]

    async def _delete_one(self, artifact: Artifact) -> RetentionOutcome:
        try:
            self._files.discard(artifact.relative_path)
        except OSError as error:
            message = safe_error_message(error)
            await self._artifacts.record_deletion_failure(artifact.id, message)
            attempts = artifact.deletion_attempts + 1
            gave_up = attempts >= self._max_attempts
            log_event(
                _logger, logging.ERROR if gave_up else logging.WARNING,
                "artifact_deletion_gave_up" if gave_up else "artifact_deletion_failed",
                artifact_id=artifact.id, attempts=attempts, error=message,
            )
            return RetentionOutcome(artifact.id, "gave_up" if gave_up else "failed", message)

        await self._artifacts.mark_deleted(artifact.id)
        log_event(_logger, logging.INFO, "artifact_deleted", artifact_id=artifact.id, size=artifact.size)
        return RetentionOutcome(artifact.id, "deleted", None)
