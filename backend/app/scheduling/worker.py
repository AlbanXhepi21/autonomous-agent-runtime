"""Run every due schedule once: claim it, execute it, reschedule it.

Scheduled execution goes through ``SavedReportExecutionService`` exactly as a
manual "run this saved report" API call does -- the same deterministic
semantic-metric pipeline, the same refusal of ``require_new_investigation``
definitions. Nothing in this module imports from ``app.llm`` or
``app.orchestration.run_manager``, and a contract test asserts it stays that
way: a schedule firing must never be how an agent investigation starts.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal, Protocol
from uuid import UUID

from app.core.logging import log_event, safe_error_message
from app.reliability.contracts import FailureCategory, RuntimeFailure
from app.reliability.retry import RetryPolicy, RetryRule, Sleep, default_sleep
from app.reports.execution import SavedReportExecutionError, SavedReportExecutionService
from app.reports.store import SavedReportStore
from app.scheduling.calculator import compute_next_run
from app.scheduling.contracts import ScheduledReportDefinition
from app.scheduling.store import ScheduledReportStore

_logger = logging.getLogger(__name__)

ScheduleRunStatus = Literal["completed", "failed", "skipped"]


@dataclass(frozen=True, slots=True)
class ScheduleRunOutcome:
    """What running one due schedule produced, for a caller's own reporting."""

    scheduled_report_id: UUID
    status: ScheduleRunStatus
    run_id: str | None
    error: str | None


class DeliveryDispatcher(Protocol):
    """The one operation a scheduler needs from a delivery service.

    A structural type rather than an import of ``app.delivery`` -- this
    module has no need to depend on how delivery is implemented, only that
    something can attempt one.
    """

    async def deliver(self, *, artifact_id: str, channel: str, destination: str) -> object: ...


_DEFAULT_RETRY_POLICY = RetryPolicy({
    ("scheduled_report", FailureCategory.SCHEDULED_REPORT_FAILURE): RetryRule(
        max_attempts=3, initial_delay_seconds=0.5, max_delay_seconds=5.0,
    ),
})


class SchedulerWorker:
    """Claim due schedules and run each through the deterministic pipeline."""

    def __init__(
        self, *, schedules: ScheduledReportStore, saved_reports: SavedReportStore,
        execution_service: SavedReportExecutionService, delivery: DeliveryDispatcher | None = None,
        retry_policy: RetryPolicy | None = None, sleep: Sleep = default_sleep,
        stale_claim_after: timedelta = timedelta(minutes=15),
    ) -> None:
        self._schedules = schedules
        self._saved_reports = saved_reports
        self._execution_service = execution_service
        self._delivery = delivery
        self._retry_policy = retry_policy or _DEFAULT_RETRY_POLICY
        self._sleep = sleep
        self._stale_claim_after = stale_claim_after

    async def run_once(self, *, batch_size: int = 10, now: datetime | None = None) -> list[ScheduleRunOutcome]:
        """Claim every currently-due schedule (up to ``batch_size``) and run each."""

        reference = now or datetime.now(timezone.utc)
        claimed = await self._schedules.claim_due(
            now=reference, stale_after=self._stale_claim_after, limit=batch_size,
        )
        outcomes = []
        for schedule in claimed:
            outcomes.append(await self._run_one(schedule, now=reference))
        return outcomes

    async def _run_one(self, schedule: ScheduledReportDefinition, *, now: datetime) -> ScheduleRunOutcome:
        definition = await self._saved_reports.get(
            workspace_id=schedule.workspace_id, saved_report_id=schedule.saved_report_id,
        )
        if definition is None or definition.status != "active":
            reason = "the saved report no longer exists" if definition is None else "the saved report is archived"
            await self._reschedule(schedule, now=now, result="skipped")
            log_event(_logger, logging.WARNING, "scheduled_report_skipped",
                      scheduled_report_id=str(schedule.id), reason=reason)
            return ScheduleRunOutcome(schedule.id, "skipped", None, reason)

        attempt = 0
        last_error: Exception | None = None
        started = time.monotonic()
        while True:
            attempt += 1
            try:
                result = await self._execution_service.execute(
                    definition, mode="publish", formats=schedule.formats, today=now.date(),
                )
            except SavedReportExecutionError as error:
                last_error = error
                failure = RuntimeFailure.from_exception(
                    error, category=FailureCategory.SCHEDULED_REPORT_FAILURE, retryable=True,
                    source="scheduled_report", attempt=attempt,
                )
                delay = self._retry_policy.retry_delay(failure)
                log_event(_logger, logging.WARNING, "scheduled_report_execution_attempt_failed",
                          scheduled_report_id=str(schedule.id), attempt=attempt,
                          error=safe_error_message(error), will_retry=delay is not None)
                if delay is None:
                    break
                await self._sleep(delay)
                continue

            latency_ms = int((time.monotonic() - started) * 1000)
            artifact_ids = [artifact.id for artifact in result.artifacts]
            await self._saved_reports.create_execution(
                saved_report_id=definition.id, run_id=result.run_id, mode="publish",
                resolved_period=(result.resolved.period.start, result.resolved.period.end),
                formats=schedule.formats, scheduled_report_id=schedule.id, retry_count=attempt - 1,
            )
            await self._saved_reports.finish_execution(
                run_id=result.run_id, status="completed", error=None,
                usage_metadata={"latency_ms": latency_ms, "artifact_count": len(result.artifacts)},
                artifact_ids=artifact_ids,
            )
            await self._reschedule(schedule, now=now, result="completed")
            log_event(_logger, logging.INFO, "scheduled_report_executed",
                      scheduled_report_id=str(schedule.id), run_id=result.run_id,
                      attempt=attempt, latency_ms=latency_ms, artifact_count=len(artifact_ids))
            if schedule.delivery_channel and schedule.delivery_destination and self._delivery is not None:
                await self._deliver_all(schedule, artifact_ids)
            return ScheduleRunOutcome(schedule.id, "completed", result.run_id, None)

        # Every attempt failed: record one failed execution, not one per attempt.
        assert last_error is not None
        failed_run_id = f"scheduled-failed-{schedule.id}-{now.timestamp()}"
        await self._saved_reports.create_execution(
            saved_report_id=definition.id, run_id=failed_run_id, mode="publish",
            resolved_period=None, formats=schedule.formats,
            scheduled_report_id=schedule.id, retry_count=attempt - 1,
        )
        await self._saved_reports.finish_execution(
            run_id=failed_run_id, status="failed", error=safe_error_message(last_error),
            error_category=FailureCategory.SCHEDULED_REPORT_FAILURE.value,
        )
        await self._reschedule(schedule, now=now, result="failed")
        log_event(_logger, logging.ERROR, "scheduled_report_failed",
                  scheduled_report_id=str(schedule.id), attempts=attempt, error=safe_error_message(last_error))
        return ScheduleRunOutcome(schedule.id, "failed", None, safe_error_message(last_error))

    async def _deliver_all(self, schedule: ScheduledReportDefinition, artifact_ids: list[str]) -> None:
        assert self._delivery is not None and schedule.delivery_channel and schedule.delivery_destination
        for artifact_id in artifact_ids:
            try:
                await self._delivery.deliver(
                    artifact_id=artifact_id, channel=schedule.delivery_channel,
                    destination=schedule.delivery_destination,
                )
            except Exception as error:  # noqa: BLE001 - a delivery failure must not fail the schedule
                log_event(_logger, logging.WARNING, "scheduled_report_delivery_failed",
                          scheduled_report_id=str(schedule.id), artifact_id=artifact_id,
                          error=safe_error_message(error))

    async def _reschedule(
        self, schedule: ScheduledReportDefinition, *, now: datetime, result: ScheduleRunStatus,
    ) -> None:
        next_run_at = compute_next_run(schedule.schedule, tz_name=schedule.timezone, after=now)
        await self._schedules.record_run_result(
            scheduled_report_id=schedule.id, ran_at=now, result=result, next_run_at=next_run_at,
        )
