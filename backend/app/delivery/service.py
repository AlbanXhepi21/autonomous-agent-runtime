"""Deliver one ready artifact through one configured channel.

"Never deliver before ready" is structural, not a check this module
performs: ``ArtifactStore.get`` already refuses to return anything but a
``READY`` artifact, so a pending, failed or deleted one is indistinguishable
from one that does not exist -- ``deliver`` raises the same ``DeliveryError``
either way.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.artifacts.store import ArtifactStore
from app.core.logging import log_event
from app.delivery.contracts import DeliveryChannel, DeliveryError, DeliveryRecord
from app.delivery.providers import DeliveryProvider
from app.delivery.store import DeliveryStore
from app.reliability.contracts import FailureCategory, RuntimeFailure
from app.reliability.retry import RetryPolicy, RetryRule, Sleep, default_sleep

_logger = logging.getLogger(__name__)

_DEFAULT_RETRY_POLICY = RetryPolicy({
    ("delivery", FailureCategory.DELIVERY_FAILURE): RetryRule(
        max_attempts=3, initial_delay_seconds=1.0, max_delay_seconds=10.0,
    ),
})


class DeliveryService:
    """Attempt a delivery, with bounded retry for transient provider failures."""

    def __init__(
        self, *, artifacts: ArtifactStore, store: DeliveryStore,
        providers: dict[DeliveryChannel, DeliveryProvider],
        retry_policy: RetryPolicy | None = None, sleep: Sleep = default_sleep,
    ) -> None:
        self._artifacts = artifacts
        self._store = store
        self._providers = providers
        self._retry_policy = retry_policy or _DEFAULT_RETRY_POLICY
        self._sleep = sleep

    async def deliver(
        self, *, workspace_id: UUID, artifact_id: str, channel: DeliveryChannel, destination: str,
    ) -> DeliveryRecord:
        artifact = await self._artifacts.get(workspace_id=workspace_id, artifact_id=artifact_id)
        if artifact is None:
            raise DeliveryError(f"Artifact {artifact_id} is not ready for delivery.")
        provider = self._providers.get(channel)
        if provider is None:
            raise DeliveryError(f"{channel} delivery is not configured on this server.")

        record = await self._store.create(
            workspace_id=workspace_id, artifact_id=artifact_id, channel=channel, destination=destination,
        )

        attempt = 0
        while True:
            attempt += 1
            result = await provider.send(artifact=artifact, destination=destination)
            if result.success:
                log_event(_logger, logging.INFO, "artifact_delivered", artifact_id=artifact_id,
                          channel=channel, attempt=attempt)
                return await self._store.record_attempt(
                    workspace_id=workspace_id, delivery_id=record.id, status="sent",
                    provider_metadata=result.provider_metadata, failure_reason=None,
                )

            # Every attempt is recorded, successful or not, so attempt_count
            # reflects how many times a destination was actually contacted --
            # not just whether the final one succeeded.
            outcome = await self._store.record_attempt(
                workspace_id=workspace_id, delivery_id=record.id, status="failed",
                provider_metadata=result.provider_metadata, failure_reason=result.failure_reason,
            )
            failure = RuntimeFailure(
                category=FailureCategory.DELIVERY_FAILURE, message=result.failure_reason or "delivery failed",
                retryable=result.retryable, source="delivery", attempt=attempt,
            )
            delay = self._retry_policy.retry_delay(failure)
            log_event(_logger, logging.WARNING, "artifact_delivery_attempt_failed", artifact_id=artifact_id,
                      channel=channel, attempt=attempt, reason=result.failure_reason, will_retry=delay is not None)
            if delay is None:
                return outcome
            await self._sleep(delay)
