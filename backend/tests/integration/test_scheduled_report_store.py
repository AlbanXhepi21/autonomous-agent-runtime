"""Scheduled report persistence and claiming, against a real database.

Skips when TEST_DATABASE_URL is unset, like the other database tests. Rows
are scoped to two workspaces minted fresh (via ``uuid4()``) for this run,
whose rows are inserted into the real ``workspaces`` table -- both
``saved_reports.workspace_id`` and ``scheduled_reports.workspace_id`` carry a
foreign key to it -- and purged, children first, on the way in and out.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from pytest_asyncio import fixture
from sqlalchemy import delete, select

pytest.importorskip("sqlalchemy")

from app.db.records import (
    SavedReportExecutionRecord,
    SavedReportRecord,
    ScheduledReportRecord,
    WorkspaceRecord,
)
from app.db.session import Database
from app.reports.contracts import RelativePeriod, SavedMetricRequest
from app.reports.store import PostgresSavedReportStore
from app.scheduling.contracts import ScheduleConfig
from app.scheduling.store import PostgresScheduledReportStore, ScheduledReportNotFoundError

pytestmark = pytest.mark.postgres

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
WORKSPACE_A: UUID = uuid4()
WORKSPACE_B: UUID = uuid4()


async def _insert_workspaces() -> None:
    database = Database(TEST_DATABASE_URL or "")
    try:
        stamp = datetime.now(timezone.utc)
        async with database.session() as session, session.begin():
            for workspace_id, suffix in ((WORKSPACE_A, "a"), (WORKSPACE_B, "b")):
                session.add(WorkspaceRecord(
                    id=workspace_id, name=f"Scheduled Report Store Test Workspace {suffix.upper()}",
                    slug=f"test-scheduled-reports-{suffix}-{workspace_id.hex[:12]}",
                    logo_ref=None, is_active=True, default_timezone="UTC",
                    default_locale="en-US", default_currency="USD",
                    created_at=stamp, updated_at=stamp,
                ))
    finally:
        await database.dispose()


async def _purge() -> None:
    database = Database(TEST_DATABASE_URL or "")
    try:
        async with database.session() as session, session.begin():
            saved_report_ids = (await session.scalars(
                select(SavedReportRecord.id)
                .where(SavedReportRecord.workspace_id.in_([WORKSPACE_A, WORKSPACE_B]))
            )).all()
            if saved_report_ids:
                await session.execute(
                    delete(SavedReportExecutionRecord)
                    .where(SavedReportExecutionRecord.saved_report_id.in_(saved_report_ids))
                )
                await session.execute(
                    delete(ScheduledReportRecord)
                    .where(ScheduledReportRecord.saved_report_id.in_(saved_report_ids))
                )
            await session.execute(
                delete(SavedReportRecord).where(SavedReportRecord.workspace_id.in_([WORKSPACE_A, WORKSPACE_B]))
            )
            # Parent last: both saved_reports.workspace_id and
            # scheduled_reports.workspace_id foreign-key to workspaces, so the
            # minted rows can only go once every child row is gone.
            await session.execute(
                delete(WorkspaceRecord).where(WorkspaceRecord.id.in_([WORKSPACE_A, WORKSPACE_B]))
            )
    finally:
        await database.dispose()


@fixture
async def rig():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    await _purge()  # defensive: clears anything a previously crashed run left behind
    await _insert_workspaces()
    database = Database(TEST_DATABASE_URL)
    try:
        yield PostgresSavedReportStore(database), PostgresScheduledReportStore(database)
    finally:
        await database.dispose()
        await _purge()


async def _saved_report(reports, *, workspace_id: UUID = WORKSPACE_A):
    return await reports.create(
        workspace_id=workspace_id, owner=None, name="Scheduled Source", description=None,
        template_id="analysis_summary", template_version="4",
        metric_requests=[SavedMetricRequest(metric="revenue")],
        default_period=RelativePeriod(kind="last_n_days", days=7),
        narrative_policy="exclude", seed_run_id=None, seed_narrative=None, seed_narrative_period=None,
    )


async def _schedule(schedules, saved_report_id, *, workspace_id: UUID = WORKSPACE_A, next_run_at=None):
    return await schedules.create(
        saved_report_id=saved_report_id, workspace_id=workspace_id,
        schedule=ScheduleConfig(kind="daily", hour=6, minute=0), timezone="UTC", formats=["pdf"],
        delivery_channel=None, delivery_destination=None,
        next_run_at=next_run_at or (datetime.now(UTC) - timedelta(minutes=1)),
    )


@pytest.mark.asyncio
async def test_a_created_schedule_round_trips_every_field(rig) -> None:
    reports, schedules = rig
    saved = await _saved_report(reports)

    created = await _schedule(schedules, saved.id)
    fetched = await schedules.get(workspace_id=WORKSPACE_A, scheduled_report_id=created.id)

    assert fetched is not None
    assert fetched.schedule.kind == "daily"
    assert fetched.timezone == "UTC"
    assert fetched.formats == ["pdf"]
    assert fetched.enabled is True
    assert fetched.consecutive_failures == 0


@pytest.mark.asyncio
async def test_listing_is_scoped_to_its_workspace(rig) -> None:
    reports, schedules = rig
    saved_a = await _saved_report(reports, workspace_id=WORKSPACE_A)
    saved_b = await _saved_report(reports, workspace_id=WORKSPACE_B)
    await _schedule(schedules, saved_a.id, workspace_id=WORKSPACE_A)
    await _schedule(schedules, saved_b.id, workspace_id=WORKSPACE_B)

    items_a, total_a = await schedules.list(workspace_id=WORKSPACE_A, enabled=None, limit=30, offset=0)
    items_b, total_b = await schedules.list(workspace_id=WORKSPACE_B, enabled=None, limit=30, offset=0)

    assert total_a == 1 and items_a[0].saved_report_id == saved_a.id
    assert total_b == 1 and items_b[0].saved_report_id == saved_b.id


@pytest.mark.asyncio
async def test_a_schedule_from_another_workspace_is_invisible_to_get(rig) -> None:
    reports, schedules = rig
    saved = await _saved_report(reports, workspace_id=WORKSPACE_A)
    created = await _schedule(schedules, saved.id, workspace_id=WORKSPACE_A)

    assert await schedules.get(workspace_id=WORKSPACE_B, scheduled_report_id=created.id) is None


@pytest.mark.asyncio
async def test_a_schedule_from_another_workspace_cannot_be_updated(rig) -> None:
    reports, schedules = rig
    saved = await _saved_report(reports, workspace_id=WORKSPACE_A)
    created = await _schedule(schedules, saved.id, workspace_id=WORKSPACE_A)

    with pytest.raises(ScheduledReportNotFoundError):
        await schedules.update(workspace_id=WORKSPACE_B, scheduled_report_id=created.id, changes={"enabled": False})


@pytest.mark.asyncio
async def test_update_changes_only_the_named_fields(rig) -> None:
    reports, schedules = rig
    saved = await _saved_report(reports)
    created = await _schedule(schedules, saved.id)

    updated = await schedules.update(
        workspace_id=WORKSPACE_A, scheduled_report_id=created.id, changes={"enabled": False},
    )

    assert updated.enabled is False
    assert updated.timezone == "UTC"
    assert updated.schedule.kind == "daily"


@pytest.mark.asyncio
async def test_claim_due_only_returns_schedules_that_are_actually_due(rig) -> None:
    reports, schedules = rig
    saved = await _saved_report(reports)
    due = await _schedule(schedules, saved.id, next_run_at=datetime.now(UTC) - timedelta(minutes=1))
    not_due = await _schedule(schedules, saved.id, next_run_at=datetime.now(UTC) + timedelta(days=1))

    claimed = await schedules.claim_due(now=datetime.now(UTC), stale_after=timedelta(minutes=15), limit=10)

    assert [item.id for item in claimed] == [due.id]
    assert not_due.id not in [item.id for item in claimed]


@pytest.mark.asyncio
async def test_a_disabled_schedule_is_never_claimed(rig) -> None:
    reports, schedules = rig
    saved = await _saved_report(reports)
    created = await _schedule(schedules, saved.id)
    await schedules.update(workspace_id=WORKSPACE_A, scheduled_report_id=created.id, changes={"enabled": False})

    claimed = await schedules.claim_due(now=datetime.now(UTC), stale_after=timedelta(minutes=15), limit=10)

    assert claimed == []


@pytest.mark.asyncio
async def test_a_claimed_schedule_is_not_claimed_again_by_a_second_worker(rig) -> None:
    reports, schedules = rig
    saved = await _saved_report(reports)
    created = await _schedule(schedules, saved.id)

    first = await schedules.claim_due(now=datetime.now(UTC), stale_after=timedelta(minutes=15), limit=10)
    second = await schedules.claim_due(now=datetime.now(UTC), stale_after=timedelta(minutes=15), limit=10)

    assert [item.id for item in first] == [created.id]
    assert second == []


@pytest.mark.asyncio
async def test_a_stale_claim_becomes_reclaimable(rig) -> None:
    reports, schedules = rig
    saved = await _saved_report(reports)
    await _schedule(schedules, saved.id)
    await schedules.claim_due(now=datetime.now(UTC), stale_after=timedelta(minutes=15), limit=10)

    reclaimed = await schedules.claim_due(now=datetime.now(UTC), stale_after=timedelta(seconds=0), limit=10)

    assert len(reclaimed) == 1


@pytest.mark.asyncio
async def test_record_run_result_completed_resets_consecutive_failures(rig) -> None:
    reports, schedules = rig
    saved = await _saved_report(reports)
    created = await _schedule(schedules, saved.id)
    await schedules.record_run_result(
        workspace_id=WORKSPACE_A, scheduled_report_id=created.id,
        ran_at=datetime.now(UTC), result="failed", next_run_at=None,
    )

    await schedules.record_run_result(
        workspace_id=WORKSPACE_A, scheduled_report_id=created.id, ran_at=datetime.now(UTC), result="completed",
        next_run_at=datetime.now(UTC) + timedelta(days=1),
    )

    after = await schedules.get(workspace_id=WORKSPACE_A, scheduled_report_id=created.id)
    assert after.last_result == "completed"
    assert after.consecutive_failures == 0


@pytest.mark.asyncio
async def test_record_run_result_failed_increments_consecutive_failures(rig) -> None:
    reports, schedules = rig
    saved = await _saved_report(reports)
    created = await _schedule(schedules, saved.id)

    await schedules.record_run_result(
        workspace_id=WORKSPACE_A, scheduled_report_id=created.id,
        ran_at=datetime.now(UTC), result="failed", next_run_at=None,
    )
    await schedules.record_run_result(
        workspace_id=WORKSPACE_A, scheduled_report_id=created.id,
        ran_at=datetime.now(UTC), result="failed", next_run_at=None,
    )

    after = await schedules.get(workspace_id=WORKSPACE_A, scheduled_report_id=created.id)
    assert after.consecutive_failures == 2


@pytest.mark.asyncio
async def test_record_run_result_skipped_does_not_change_consecutive_failures(rig) -> None:
    reports, schedules = rig
    saved = await _saved_report(reports)
    created = await _schedule(schedules, saved.id)
    await schedules.record_run_result(
        workspace_id=WORKSPACE_A, scheduled_report_id=created.id,
        ran_at=datetime.now(UTC), result="failed", next_run_at=None,
    )

    await schedules.record_run_result(
        workspace_id=WORKSPACE_A, scheduled_report_id=created.id,
        ran_at=datetime.now(UTC), result="skipped", next_run_at=None,
    )

    after = await schedules.get(workspace_id=WORKSPACE_A, scheduled_report_id=created.id)
    assert after.consecutive_failures == 1


@pytest.mark.asyncio
async def test_record_run_result_releases_the_claim(rig) -> None:
    reports, schedules = rig
    saved = await _saved_report(reports)
    created = await _schedule(schedules, saved.id)
    await schedules.claim_due(now=datetime.now(UTC), stale_after=timedelta(minutes=15), limit=10)

    await schedules.record_run_result(
        workspace_id=WORKSPACE_A, scheduled_report_id=created.id, ran_at=datetime.now(UTC), result="completed",
        next_run_at=datetime.now(UTC) + timedelta(days=1),
    )

    reclaimed = await schedules.claim_due(now=datetime.now(UTC), stale_after=timedelta(minutes=15), limit=10)
    assert reclaimed == []  # next_run_at was pushed to the future, not just unclaimed
