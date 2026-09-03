"""Running due schedules: success, retry-then-fail, skip, and delivery dispatch.

Every dependency is a fake here -- the real pipeline (SavedReportExecutionService
against a live analytics database) is already exercised end to end by
tests/unit/reports/test_execution.py and the saved-report integration suite.
This module is about what SchedulerWorker itself is responsible for: claiming,
retrying, persisting an execution record, rescheduling, and never calling an
LLM to do any of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest

from app.analytics.semantics.parameters import ReportPeriod
from app.artifacts.contracts import Artifact, ArtifactStatus
from app.reports.contracts import RelativePeriod, SavedMetricRequest, SavedReportDefinition
from app.reports.execution import SavedReportExecutionError, SavedReportExecutionResult
from app.reports.periods import ResolvedPeriod
from app.scheduling.contracts import ScheduleConfig, ScheduledReportDefinition
from app.scheduling.worker import SchedulerWorker


WORKSPACE_ID = uuid4()


def _saved_report(**overrides) -> SavedReportDefinition:
    now = datetime.now(UTC)
    fields = dict(
        id=uuid4(), workspace_id=WORKSPACE_ID, owner=None, name="Weekly Revenue", description=None,
        template_id="analysis_summary", template_version="4",
        metric_requests=[SavedMetricRequest(metric="revenue")],
        default_period=RelativePeriod(kind="last_n_days", days=7),
        narrative_policy="exclude", seed_run_id=None, seed_narrative=None, seed_narrative_period=None,
        version=1, status="active", created_at=now, updated_at=now,
    )
    fields.update(overrides)
    return SavedReportDefinition(**fields)


def _schedule(**overrides) -> ScheduledReportDefinition:
    now = datetime.now(UTC)
    fields = dict(
        id=uuid4(), saved_report_id=uuid4(), workspace_id=WORKSPACE_ID,
        schedule=ScheduleConfig(kind="daily", hour=6, minute=0), timezone="UTC", formats=["pdf"],
        delivery_channel=None, delivery_destination=None, enabled=True, next_run_at=now,
        last_run_at=None, last_result=None, consecutive_failures=0, created_at=now, updated_at=now,
    )
    fields.update(overrides)
    return ScheduledReportDefinition(**fields)


def _artifact(artifact_id: str = "artifact-1") -> Artifact:
    return Artifact(
        id=artifact_id, workspace_id=WORKSPACE_ID, name="report.pdf",
        relative_path=f"artifacts/run/{artifact_id}/report.pdf",
        artifact_type="report_document", media_type="application/pdf", size=1234, sha256="0" * 64,
        status=ArtifactStatus.READY, run_id="run-1", created_at=datetime.now(UTC),
    )


def _result(run_id: str = "saved-report-run-1") -> SavedReportExecutionResult:
    return SavedReportExecutionResult(
        run_id=run_id,
        resolved=ResolvedPeriod(period=ReportPeriod(start=date(2026, 1, 1), end=date(2026, 1, 8)), description="d"),
        preview=None, artifacts=[_artifact()],
    )


@dataclass
class FakeExecutionService:
    results: list[object] = field(default_factory=list)
    calls: list[tuple] = field(default_factory=list)

    async def execute(self, definition, *, mode, formats=None, today=None):
        self.calls.append((definition.id, mode, tuple(formats or []), today))
        outcome = self.results.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@dataclass
class FakeSavedReportStore:
    reports: dict[UUID, SavedReportDefinition] = field(default_factory=dict)
    executions: list[dict] = field(default_factory=list)
    finished: list[dict] = field(default_factory=list)

    async def get(self, *, workspace_id, saved_report_id):
        report = self.reports.get(saved_report_id)
        return report if report is not None and report.workspace_id == workspace_id else None

    async def create_execution(self, **kwargs):
        self.executions.append(kwargs)
        return None

    async def finish_execution(self, **kwargs):
        self.finished.append(kwargs)


@dataclass
class FakeScheduledReportStore:
    due: list[ScheduledReportDefinition] = field(default_factory=list)
    results: list[dict] = field(default_factory=list)

    async def claim_due(self, *, now, stale_after, limit):
        claimed, self.due = self.due[:limit], self.due[limit:]
        return claimed

    async def record_run_result(self, *, workspace_id, scheduled_report_id, ran_at, result, next_run_at):
        self.results.append({
            "workspace_id": workspace_id, "scheduled_report_id": scheduled_report_id, "ran_at": ran_at,
            "result": result, "next_run_at": next_run_at,
        })


@dataclass
class FakeDelivery:
    calls: list[tuple] = field(default_factory=list)
    should_fail: bool = False

    async def deliver(self, *, workspace_id, artifact_id, channel, destination):
        self.calls.append((artifact_id, channel, destination))
        if self.should_fail:
            raise RuntimeError("delivery unavailable")
        return object()


async def _no_sleep(delay: float) -> None:
    return None


@pytest.mark.asyncio
async def test_a_successful_run_persists_completion_and_reschedules() -> None:
    saved = _saved_report()
    schedule = _schedule(saved_report_id=saved.id)
    reports = FakeSavedReportStore(reports={saved.id: saved})
    schedules = FakeScheduledReportStore(due=[schedule])
    execution = FakeExecutionService(results=[_result()])
    worker = SchedulerWorker(schedules=schedules, saved_reports=reports, execution_service=execution)

    outcomes = await worker.run_once()

    assert len(outcomes) == 1
    assert outcomes[0].status == "completed"
    assert outcomes[0].run_id == "saved-report-run-1"
    assert reports.executions[0]["scheduled_report_id"] == schedule.id
    assert reports.executions[0]["retry_count"] == 0
    assert reports.finished[0]["status"] == "completed"
    assert reports.finished[0]["artifact_ids"] == ["artifact-1"]
    assert schedules.results[0]["result"] == "completed"
    assert schedules.results[0]["next_run_at"] > datetime.now(UTC)


@pytest.mark.asyncio
async def test_execution_always_publishes_never_previews() -> None:
    """A schedule fires to produce an artifact -- there is nothing to preview toward."""

    saved = _saved_report()
    schedule = _schedule(saved_report_id=saved.id, formats=["pdf", "docx"])
    reports = FakeSavedReportStore(reports={saved.id: saved})
    schedules = FakeScheduledReportStore(due=[schedule])
    execution = FakeExecutionService(results=[_result()])
    worker = SchedulerWorker(schedules=schedules, saved_reports=reports, execution_service=execution)

    await worker.run_once()

    (_, mode, formats, _), = execution.calls
    assert mode == "publish"
    assert formats == ("pdf", "docx")


@pytest.mark.asyncio
async def test_a_transient_failure_is_retried_before_being_recorded_as_failed() -> None:
    saved = _saved_report()
    schedule = _schedule(saved_report_id=saved.id)
    reports = FakeSavedReportStore(reports={saved.id: saved})
    schedules = FakeScheduledReportStore(due=[schedule])
    execution = FakeExecutionService(results=[
        SavedReportExecutionError("transient"), SavedReportExecutionError("transient"), _result(),
    ])
    worker = SchedulerWorker(schedules=schedules, saved_reports=reports, execution_service=execution, sleep=_no_sleep)

    outcomes = await worker.run_once()

    assert outcomes[0].status == "completed"
    assert len(execution.calls) == 3
    assert reports.executions[0]["retry_count"] == 2  # two failed attempts before the one that landed


@pytest.mark.asyncio
async def test_exhausting_every_retry_records_one_failed_execution() -> None:
    saved = _saved_report()
    schedule = _schedule(saved_report_id=saved.id)
    reports = FakeSavedReportStore(reports={saved.id: saved})
    schedules = FakeScheduledReportStore(due=[schedule])
    execution = FakeExecutionService(results=[
        SavedReportExecutionError("boom"), SavedReportExecutionError("boom"), SavedReportExecutionError("boom"),
    ])
    worker = SchedulerWorker(schedules=schedules, saved_reports=reports, execution_service=execution, sleep=_no_sleep)

    outcomes = await worker.run_once()

    assert outcomes[0].status == "failed"
    assert outcomes[0].error is not None
    # Exactly one execution record for the whole attempt sequence, not one per try.
    assert len(reports.executions) == 1
    assert len(reports.finished) == 1
    assert reports.finished[0]["status"] == "failed"
    assert reports.finished[0]["error_category"] == "scheduled_report_failure"
    assert schedules.results[0]["result"] == "failed"


@pytest.mark.asyncio
async def test_a_missing_saved_report_is_skipped_not_failed() -> None:
    schedule = _schedule(saved_report_id=uuid4())
    reports = FakeSavedReportStore(reports={})
    schedules = FakeScheduledReportStore(due=[schedule])
    execution = FakeExecutionService(results=[])
    worker = SchedulerWorker(schedules=schedules, saved_reports=reports, execution_service=execution)

    outcomes = await worker.run_once()

    assert outcomes[0].status == "skipped"
    assert execution.calls == []
    assert schedules.results[0]["result"] == "skipped"


@pytest.mark.asyncio
async def test_an_archived_saved_report_is_skipped() -> None:
    saved = _saved_report(status="archived")
    schedule = _schedule(saved_report_id=saved.id)
    reports = FakeSavedReportStore(reports={saved.id: saved})
    schedules = FakeScheduledReportStore(due=[schedule])
    execution = FakeExecutionService(results=[])
    worker = SchedulerWorker(schedules=schedules, saved_reports=reports, execution_service=execution)

    outcomes = await worker.run_once()

    assert outcomes[0].status == "skipped"
    assert execution.calls == []


@pytest.mark.asyncio
async def test_a_successful_run_with_delivery_configured_dispatches_it() -> None:
    saved = _saved_report()
    schedule = _schedule(
        saved_report_id=saved.id, delivery_channel="webhook", delivery_destination="https://example.com/hook",
    )
    reports = FakeSavedReportStore(reports={saved.id: saved})
    schedules = FakeScheduledReportStore(due=[schedule])
    execution = FakeExecutionService(results=[_result()])
    delivery = FakeDelivery()
    worker = SchedulerWorker(schedules=schedules, saved_reports=reports, execution_service=execution, delivery=delivery)

    await worker.run_once()

    assert delivery.calls == [("artifact-1", "webhook", "https://example.com/hook")]


@pytest.mark.asyncio
async def test_a_delivery_failure_does_not_fail_the_schedule() -> None:
    saved = _saved_report()
    schedule = _schedule(
        saved_report_id=saved.id, delivery_channel="webhook", delivery_destination="https://example.com/hook",
    )
    reports = FakeSavedReportStore(reports={saved.id: saved})
    schedules = FakeScheduledReportStore(due=[schedule])
    execution = FakeExecutionService(results=[_result()])
    delivery = FakeDelivery(should_fail=True)
    worker = SchedulerWorker(schedules=schedules, saved_reports=reports, execution_service=execution, delivery=delivery)

    outcomes = await worker.run_once()

    assert outcomes[0].status == "completed"


@pytest.mark.asyncio
async def test_no_delivery_is_attempted_when_none_is_configured() -> None:
    saved = _saved_report()
    schedule = _schedule(saved_report_id=saved.id)  # no delivery_channel
    reports = FakeSavedReportStore(reports={saved.id: saved})
    schedules = FakeScheduledReportStore(due=[schedule])
    execution = FakeExecutionService(results=[_result()])
    delivery = FakeDelivery()
    worker = SchedulerWorker(schedules=schedules, saved_reports=reports, execution_service=execution, delivery=delivery)

    await worker.run_once()

    assert delivery.calls == []


@pytest.mark.asyncio
async def test_nothing_due_produces_no_outcomes() -> None:
    reports = FakeSavedReportStore()
    schedules = FakeScheduledReportStore(due=[])
    execution = FakeExecutionService(results=[])
    worker = SchedulerWorker(schedules=schedules, saved_reports=reports, execution_service=execution)

    outcomes = await worker.run_once()

    assert outcomes == []
