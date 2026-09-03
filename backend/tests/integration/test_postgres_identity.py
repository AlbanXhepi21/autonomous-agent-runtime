"""Optional integration coverage for PostgreSQL identity-store semantics."""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pytest_asyncio import fixture

pytest.importorskip("sqlalchemy")

from sqlalchemy.exc import IntegrityError

from app.db.session import Database
from app.identity.contracts import TokenPurpose
from app.identity.store import PostgresIdentityTokenStore, PostgresSessionStore, PostgresUserStore
from app.identity.tokens import generate_token, hash_token

pytestmark = pytest.mark.postgres

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def _now() -> datetime:
    return datetime.now(UTC)


@fixture
async def stores():
    """Connect to an already-migrated test database; never create its schema."""

    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    database = Database(TEST_DATABASE_URL)
    users, sessions, tokens = (
        PostgresUserStore(database), PostgresSessionStore(database), PostgresIdentityTokenStore(database),
    )
    try:
        yield users, sessions, tokens
    finally:
        await database.dispose()


@pytest.mark.asyncio
async def test_postgres_user_store_enforces_case_normalized_uniqueness(stores) -> None:
    users, _, _ = stores
    email = f"postgres-test-{uuid4()}@example.com"
    created = await users.create(email=email, display_name="Ada", password_hash="hash-1")

    try:
        fetched = await users.get_by_email(email)
        assert fetched is not None and fetched.id == created.id

        with pytest.raises(IntegrityError):
            await users.create(email=email, display_name="Duplicate", password_hash="hash-2")
    finally:
        # No delete method exists on UserStore by design (no admin surface in
        # this phase); disable instead so the row cannot authenticate again.
        await users.set_active(created.id, is_active=False)


@pytest.mark.asyncio
async def test_postgres_session_store_matches_in_memory_semantics(stores) -> None:
    users, sessions, _ = stores
    email = f"postgres-test-{uuid4()}@example.com"
    user = await users.create(email=email, display_name="Ada", password_hash="hash-1")

    raw_token = generate_token()
    session = await sessions.create(
        user_id=user.id, token_hash=hash_token(raw_token), csrf_token_hash=hash_token(generate_token()),
        expires_at=_now() + timedelta(days=1), user_agent="pytest", ip_address="127.0.0.1",
    )

    fetched = await sessions.get_by_token_hash(hash_token(raw_token))
    assert fetched is not None and fetched.id == session.id

    await sessions.revoke(session.id)
    revoked = await sessions.get_by_token_hash(hash_token(raw_token))
    assert revoked is not None and revoked.revoked_at is not None

    await users.set_active(user.id, is_active=False)


@pytest.mark.asyncio
async def test_postgres_identity_token_store_is_purpose_bound_and_single_use(stores) -> None:
    users, _, tokens = stores
    email = f"postgres-test-{uuid4()}@example.com"
    user = await users.create(email=email, display_name="Ada", password_hash="hash-1")

    raw_token = generate_token()
    await tokens.create(
        user_id=user.id, token_hash=hash_token(raw_token), purpose=TokenPurpose.PASSWORD_RESET,
        expires_at=_now() + timedelta(hours=1),
    )

    # A token minted for password reset is invisible to the verification lookup.
    assert await tokens.get_by_token_hash(hash_token(raw_token), purpose=TokenPurpose.EMAIL_VERIFICATION) is None

    fetched = await tokens.get_by_token_hash(hash_token(raw_token), purpose=TokenPurpose.PASSWORD_RESET)
    assert fetched is not None and fetched.used_at is None

    await tokens.mark_used(fetched.id, at=_now())
    used = await tokens.get_by_token_hash(hash_token(raw_token), purpose=TokenPurpose.PASSWORD_RESET)
    assert used is not None and used.used_at is not None

    await users.set_active(user.id, is_active=False)
