"""Durable persistence for saved report definitions, against a real database.

Skips when TEST_DATABASE_URL is unset, like the other database tests. Every
row this suite writes is scoped to workspaces named ``test-saved-reports-*``
and purged on the way in and out, so a run never sees another run's leftovers
and never collides with a developer's own local data.
"""

from __future__ import annotations

import os
from datetime import date

import pytest
from pytest_asyncio import fixture
from sqlalchemy import delete, select

pytest.importorskip("sqlalchemy")

from app.db.records import SavedReportExecutionRecord, SavedReportRecord
from app.db.session import Database
from app.reports.contracts import RelativePeriod, SavedMetricRequest
from app.reports.store import (
    PostgresSavedReportStore,
    SavedReportNotFoundError,
    SavedReportVersionConflictError,
)

pytestmark = pytest.mark.postgres

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
WORKSPACE_A = "test-saved-reports-a"
WORKSPACE_B = "test-saved-reports-b"


async def _purge() -> None:
    database = Database(TEST_DATABASE_URL or "")
    try:
        async with database.session() as session, session.begin():
            ids = (await session.scalars(
                select(SavedReportRecord.id)
                .where(SavedReportRecord.workspace_id.in_([WORKSPACE_A, WORKSPACE_B]))
            )).all()
            if ids:
                # Children first: saved_report_executions has a
                # RESTRICT foreign key back to saved_reports.
                await session.execute(
                    delete(SavedReportExecutionRecord)
                    .where(SavedReportExecutionRecord.saved_report_id.in_(ids))
                )
            await session.execute(
                delete(SavedReportRecord)
                .where(SavedReportRecord.workspace_id.in_([WORKSPACE_A, WORKSPACE_B]))
            )
    finally:
        await database.dispose()


@fixture
async def store():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    await _purge()
    database = Database(TEST_DATABASE_URL)
    try:
        yield PostgresSavedReportStore(database)
    finally:
        await database.dispose()
        await _purge()


def _period() -> RelativePeriod:
    return RelativePeriod(kind="last_n_days", days=7)


async def _create(store, *, workspace_id: str = WORKSPACE_A, **overrides):
    fields = dict(
        workspace_id=workspace_id, owner=None, name="Weekly Revenue", description=None,
        template_id="analysis_summary", template_version="4",
        metric_requests=[SavedMetricRequest(metric="revenue")], default_period=_period(),
        narrative_policy="exclude", seed_run_id=None, seed_narrative=None, seed_narrative_period=None,
    )
    fields.update(overrides)
    return await store.create(**fields)


@pytest.mark.asyncio
async def test_a_created_definition_round_trips_every_field(store) -> None:
    created = await _create(
        store, name="Monthly Ops Review", description="For the ops standup",
        metric_requests=[SavedMetricRequest(metric="revenue"), SavedMetricRequest(metric="orders", dimensions=["country"])],
        default_period=RelativePeriod(kind="current_quarter"),
    )

    fetched = await store.get(workspace_id=WORKSPACE_A, saved_report_id=created.id)

    assert fetched is not None
    assert fetched.name == "Monthly Ops Review"
    assert fetched.description == "For the ops standup"
    assert [item.metric for item in fetched.metric_requests] == ["revenue", "orders"]
    assert fetched.metric_requests[1].dimensions == ["country"]
    assert fetched.default_period.kind == "current_quarter"
    assert fetched.version == 1
    assert fetched.status == "active"


@pytest.mark.asyncio
async def test_a_new_definition_starts_at_version_one_and_active(store) -> None:
    created = await _create(store)

    assert created.version == 1
    assert created.status == "active"


@pytest.mark.asyncio
async def test_listing_is_scoped_to_its_workspace(store) -> None:
    await _create(store, workspace_id=WORKSPACE_A, name="A's report")
    await _create(store, workspace_id=WORKSPACE_B, name="B's report")

    items_a, total_a = await store.list(workspace_id=WORKSPACE_A, status=None, limit=30, offset=0)
    items_b, total_b = await store.list(workspace_id=WORKSPACE_B, status=None, limit=30, offset=0)

    assert total_a == 1 and [item.name for item in items_a] == ["A's report"]
    assert total_b == 1 and [item.name for item in items_b] == ["B's report"]


@pytest.mark.asyncio
async def test_a_definition_from_another_workspace_is_invisible_to_get(store) -> None:
    created = await _create(store, workspace_id=WORKSPACE_A)

    assert await store.get(workspace_id=WORKSPACE_B, saved_report_id=created.id) is None


@pytest.mark.asyncio
async def test_a_definition_from_another_workspace_cannot_be_updated(store) -> None:
    created = await _create(store, workspace_id=WORKSPACE_A)

    with pytest.raises(SavedReportNotFoundError):
        await store.update(
            workspace_id=WORKSPACE_B, saved_report_id=created.id, expected_version=1,
            changes={"name": "Hijacked"},
        )


@pytest.mark.asyncio
async def test_executions_from_another_workspace_are_not_listed(store) -> None:
    created = await _create(store, workspace_id=WORKSPACE_A)
    await store.create_execution(
        saved_report_id=created.id, run_id="saved-report-isolation-test", mode="preview",
        resolved_period=(date(2026, 1, 1), date(2026, 1, 8)), formats=None,
    )

    outcome = await store.list_executions(
        workspace_id=WORKSPACE_B, saved_report_id=created.id, limit=30, offset=0,
    )

    assert outcome is None


@pytest.mark.asyncio
async def test_update_applies_only_the_named_changes(store) -> None:
    created = await _create(store, name="Original Name", description="Original description")

    updated = await store.update(
        workspace_id=WORKSPACE_A, saved_report_id=created.id, expected_version=1,
        changes={"name": "New Name"},
    )

    assert updated.name == "New Name"
    assert updated.description == "Original description"
    assert updated.version == 2


@pytest.mark.asyncio
async def test_update_bumps_the_version_and_updated_at(store) -> None:
    created = await _create(store)

    updated = await store.update(
        workspace_id=WORKSPACE_A, saved_report_id=created.id, expected_version=1,
        changes={"name": "Renamed"},
    )

    assert updated.version == 2
    assert updated.updated_at >= created.updated_at


@pytest.mark.asyncio
async def test_a_stale_expected_version_is_refused(store) -> None:
    created = await _create(store)
    await store.update(
        workspace_id=WORKSPACE_A, saved_report_id=created.id, expected_version=1,
        changes={"name": "First edit"},
    )

    with pytest.raises(SavedReportVersionConflictError) as excinfo:
        await store.update(
            workspace_id=WORKSPACE_A, saved_report_id=created.id, expected_version=1,
            changes={"name": "Conflicting edit"},
        )

    assert excinfo.value.expected == 1
    assert excinfo.value.actual == 2

    # And the first edit's value survived -- the conflicting write never landed.
    fetched = await store.get(workspace_id=WORKSPACE_A, saved_report_id=created.id)
    assert fetched is not None and fetched.name == "First edit"


@pytest.mark.asyncio
async def test_updating_a_missing_definition_is_refused(store) -> None:
    from uuid import uuid4

    with pytest.raises(SavedReportNotFoundError):
        await store.update(
            workspace_id=WORKSPACE_A, saved_report_id=uuid4(), expected_version=1, changes={"name": "x"},
        )


@pytest.mark.asyncio
async def test_an_update_that_would_break_a_cross_field_rule_is_rejected(store) -> None:
    """model_validate re-runs every validator, so a partial update cannot bypass one."""

    created = await _create(store, narrative_policy="exclude")

    with pytest.raises(ValueError, match="seed_narrative"):
        await store.update(
            workspace_id=WORKSPACE_A, saved_report_id=created.id, expected_version=1,
            changes={"narrative_policy": "include_original"},
        )


@pytest.mark.asyncio
async def test_archiving_sets_status_without_touching_other_fields(store) -> None:
    created = await _create(store, name="To Be Archived")

    archived = await store.update(
        workspace_id=WORKSPACE_A, saved_report_id=created.id, expected_version=1,
        changes={"status": "archived"},
    )

    assert archived.status == "archived"
    assert archived.name == "To Be Archived"

    active_only, active_total = await store.list(workspace_id=WORKSPACE_A, status="active", limit=30, offset=0)
    archived_only, archived_total = await store.list(workspace_id=WORKSPACE_A, status="archived", limit=30, offset=0)
    assert active_total == 0
    assert archived_total == 1 and archived_only[0].id == created.id


@pytest.mark.asyncio
async def test_an_execution_lifecycle_from_running_to_completed(store) -> None:
    created = await _create(store)

    execution = await store.create_execution(
        saved_report_id=created.id, run_id="saved-report-lifecycle-test", mode="publish",
        resolved_period=(date(2026, 1, 1), date(2026, 1, 8)), formats=["pdf"],
    )
    assert execution.status == "running"
    assert execution.completed_at is None

    await store.finish_execution(run_id="saved-report-lifecycle-test", status="completed", error=None)

    executions, total = await store.list_executions(
        workspace_id=WORKSPACE_A, saved_report_id=created.id, limit=30, offset=0,
    )
    assert total == 1
    assert executions[0].status == "completed"
    assert executions[0].completed_at is not None
    assert executions[0].resolved_period_start == date(2026, 1, 1)
    assert executions[0].resolved_period_end == date(2026, 1, 8)
    assert executions[0].formats == ["pdf"]


@pytest.mark.asyncio
async def test_a_failed_execution_records_its_error(store) -> None:
    created = await _create(store)
    await store.create_execution(
        saved_report_id=created.id, run_id="saved-report-failure-test", mode="preview",
        resolved_period=None, formats=None,
    )

    await store.finish_execution(
        run_id="saved-report-failure-test", status="failed", error="The compiled metric query failed to validate.",
    )

    executions, _total = await store.list_executions(
        workspace_id=WORKSPACE_A, saved_report_id=created.id, limit=30, offset=0,
    )
    assert executions[0].status == "failed"
    assert executions[0].error == "The compiled metric query failed to validate."


@pytest.mark.asyncio
async def test_execution_history_is_newest_first(store) -> None:
    created = await _create(store)
    await store.create_execution(
        saved_report_id=created.id, run_id="saved-report-history-1", mode="preview",
        resolved_period=None, formats=None,
    )
    await store.create_execution(
        saved_report_id=created.id, run_id="saved-report-history-2", mode="preview",
        resolved_period=None, formats=None,
    )

    executions, total = await store.list_executions(
        workspace_id=WORKSPACE_A, saved_report_id=created.id, limit=30, offset=0,
    )

    assert total == 2
    assert [item.run_id for item in executions] == ["saved-report-history-2", "saved-report-history-1"]
