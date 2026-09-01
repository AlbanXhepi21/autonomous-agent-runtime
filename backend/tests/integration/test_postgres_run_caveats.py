"""Optional integration coverage for caveats surviving the database round trip.

A caveat is only useful if it is still there when the report is published, which
may be days later and in another process. That is a claim about a column, so it
is checked against a real one.
"""

import os
from uuid import uuid4

import pytest
from pytest_asyncio import fixture

pytest.importorskip("sqlalchemy")

from sqlalchemy import delete

from app.conversations.store import PostgresConversationStore
from app.db.records import AgentRunRecord, ConversationRecord, MessageRecord
from app.db.session import Database

pytestmark = pytest.mark.postgres

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

CAVEATS = [
    "Refund timing may differ from order timing.",
    "August 2026 is a partial month, so the total understates the period.",
]


@fixture
async def database():
    """Connect to an already-migrated test database; never create its schema."""

    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    built = Database(TEST_DATABASE_URL)
    try:
        yield built
    finally:
        await built.dispose()


async def _purge(database: Database, conversation_id) -> None:
    async with database.session() as session:
        async with session.begin():
            await session.execute(delete(AgentRunRecord).where(AgentRunRecord.conversation_id == conversation_id))
            await session.execute(delete(MessageRecord).where(MessageRecord.conversation_id == conversation_id))
            await session.execute(delete(ConversationRecord).where(ConversationRecord.id == conversation_id))


async def _finished_run(database: Database, caveats: list[str] | None):
    """Create and complete one run, returning its conversation and run identifiers."""

    store = PostgresConversationStore(database)
    conversation, _, run = await store.create_run(
        conversation_id=None, message="Investigate refunds", run_id=f"caveat-test-{uuid4()}"
    )
    from datetime import UTC, datetime

    await store.finish_run(
        run_id=run.id, status="completed", completed_at=datetime.now(UTC), metrics=None,
        chart_specs=None, answer_sources=None, answer_caveats=caveats, error=None,
        assistant_content="Revenue grew 18%.",
    )
    return conversation.id, run.id


@pytest.mark.asyncio
async def test_stated_caveats_are_read_back_by_a_later_store(database) -> None:
    conversation_id, run_id = await _finished_run(database, CAVEATS)
    try:
        # A store built afterwards knows these only because the column holds them.
        reloaded = await PostgresConversationStore(database).get_run(run_id)

        assert reloaded is not None
        assert reloaded.answer_caveats == CAVEATS
    finally:
        await _purge(database, conversation_id)


@pytest.mark.asyncio
async def test_a_run_that_stated_nothing_stores_an_empty_list(database) -> None:
    conversation_id, run_id = await _finished_run(database, [])
    try:
        reloaded = await PostgresConversationStore(database).get_run(run_id)

        assert reloaded is not None
        assert reloaded.answer_caveats == []
    finally:
        await _purge(database, conversation_id)


@pytest.mark.asyncio
async def test_an_unfinished_run_records_no_caveats(database) -> None:
    """A run with no answer has nothing for a limitation to qualify."""

    conversation_id, run_id = await _finished_run(database, None)
    try:
        reloaded = await PostgresConversationStore(database).get_run(run_id)

        assert reloaded is not None
        assert reloaded.answer_caveats is None
    finally:
        await _purge(database, conversation_id)


@pytest.mark.asyncio
async def test_text_is_stored_verbatim_including_markup(database) -> None:
    hostile = ["<script>alert(1)</script> Sample of 12 orders & falling."]
    conversation_id, run_id = await _finished_run(database, hostile)
    try:
        reloaded = await PostgresConversationStore(database).get_run(run_id)

        assert reloaded is not None
        assert reloaded.answer_caveats == hostile
    finally:
        await _purge(database, conversation_id)
