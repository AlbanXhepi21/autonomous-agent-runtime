"""Delivery persistence against a real database.

Exercises the one design decision worth a database-level test: artifact_id
carries no foreign key (the artifact backend is switchable between in-memory
and PostgreSQL), so a delivery must be creatable and queryable for an
artifact id this database has never seen.

Skips when TEST_DATABASE_URL is unset, like the other database tests.
"""

from __future__ import annotations

import os

import pytest
from pytest_asyncio import fixture
from sqlalchemy import delete

pytest.importorskip("sqlalchemy")

from app.db.records import DeliveryRecord
from app.db.session import Database
from app.delivery.store import PostgresDeliveryStore

pytestmark = pytest.mark.postgres

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
ARTIFACT_ID = "test-delivery-store-artifact"


async def _purge() -> None:
    database = Database(TEST_DATABASE_URL or "")
    try:
        async with database.session() as session, session.begin():
            await session.execute(delete(DeliveryRecord).where(DeliveryRecord.artifact_id == ARTIFACT_ID))
    finally:
        await database.dispose()


@fixture
async def store():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    await _purge()
    database = Database(TEST_DATABASE_URL)
    try:
        yield PostgresDeliveryStore(database)
    finally:
        await database.dispose()
        await _purge()


@pytest.mark.asyncio
async def test_create_succeeds_for_an_artifact_id_with_no_backing_row(store) -> None:
    """No foreign key: the artifact may live in an in-memory store, not this database."""

    record = await store.create(artifact_id=ARTIFACT_ID, channel="webhook", destination="https://example.com/hook")

    assert record.artifact_id == ARTIFACT_ID
    assert record.status == "pending"
    assert record.attempt_count == 0


@pytest.mark.asyncio
async def test_record_attempt_increments_attempt_count_and_updates_status(store) -> None:
    created = await store.create(artifact_id=ARTIFACT_ID, channel="link", destination="n/a")

    first = await store.record_attempt(
        delivery_id=created.id, status="failed", provider_metadata={"status_code": 503}, failure_reason="down",
    )
    second = await store.record_attempt(
        delivery_id=created.id, status="sent", provider_metadata={"status_code": 200}, failure_reason=None,
    )

    assert first.attempt_count == 1 and first.status == "failed"
    assert second.attempt_count == 2 and second.status == "sent" and second.failure_reason is None


@pytest.mark.asyncio
async def test_get_and_list_reflect_the_latest_state(store) -> None:
    created = await store.create(artifact_id=ARTIFACT_ID, channel="email", destination="a@b.com")
    await store.record_attempt(
        delivery_id=created.id, status="sent", provider_metadata={"link": "https://x"}, failure_reason=None,
    )

    fetched = await store.get(created.id)
    listed = await store.list(artifact_id=ARTIFACT_ID)

    assert fetched is not None and fetched.status == "sent"
    assert len(listed) == 1 and listed[0].id == created.id


@pytest.mark.asyncio
async def test_list_can_filter_by_status(store) -> None:
    sent = await store.create(artifact_id=ARTIFACT_ID, channel="link", destination="n/a")
    await store.record_attempt(delivery_id=sent.id, status="sent", provider_metadata={}, failure_reason=None)
    failed = await store.create(artifact_id=ARTIFACT_ID, channel="webhook", destination="https://example.com")
    await store.record_attempt(delivery_id=failed.id, status="failed", provider_metadata={}, failure_reason="timeout")

    sent_only = await store.list(artifact_id=ARTIFACT_ID, status="sent")
    failed_only = await store.list(artifact_id=ARTIFACT_ID, status="failed")

    assert [item.id for item in sent_only] == [sent.id]
    assert [item.id for item in failed_only] == [failed.id]
