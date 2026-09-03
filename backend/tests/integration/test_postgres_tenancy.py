"""Optional integration coverage for PostgreSQL tenancy-store semantics."""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pytest_asyncio import fixture

pytest.importorskip("sqlalchemy")

from sqlalchemy.exc import IntegrityError

from app.db.session import Database
from app.identity.store import PostgresUserStore
from app.identity.tokens import generate_token, hash_token
from app.tenancy.contracts import MembershipStatus, Role
from app.tenancy.store import PostgresInvitationStore, PostgresMembershipStore, PostgresWorkspaceStore

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
    users = PostgresUserStore(database)
    workspaces, memberships, invitations = (
        PostgresWorkspaceStore(database), PostgresMembershipStore(database), PostgresInvitationStore(database),
    )
    try:
        yield users, workspaces, memberships, invitations
    finally:
        await database.dispose()


@pytest.mark.asyncio
async def test_postgres_workspace_store_enforces_slug_uniqueness(stores) -> None:
    _, workspaces, _, _ = stores
    slug = f"postgres-test-{uuid4()}"
    created = await workspaces.create(
        name="Acme", slug=slug, logo_ref=None, default_timezone="UTC", default_locale="en-US", default_currency="USD",
    )

    try:
        fetched = await workspaces.get_by_slug(slug)
        assert fetched is not None and fetched.id == created.id

        with pytest.raises(IntegrityError):
            await workspaces.create(
                name="Acme Two", slug=slug, logo_ref=None, default_timezone="UTC",
                default_locale="en-US", default_currency="USD",
            )
    finally:
        await workspaces.update(created.id, changes={"is_active": False})


@pytest.mark.asyncio
async def test_postgres_membership_store_enforces_one_row_per_user_workspace(stores) -> None:
    users, workspaces, memberships, _ = stores
    user = await users.create(
        email=f"postgres-tenancy-{uuid4()}@example.com", display_name="Ada", password_hash="hash-1",
    )
    workspace = await workspaces.create(
        name="Acme", slug=f"postgres-test-{uuid4()}", logo_ref=None, default_timezone="UTC",
        default_locale="en-US", default_currency="USD",
    )

    try:
        first = await memberships.create(
            user_id=user.id, workspace_id=workspace.id, role=Role.OWNER, status=MembershipStatus.ACTIVE,
            invited_by=None, joined_at=_now(),
        )
        fetched = await memberships.get_for_user(workspace_id=workspace.id, user_id=user.id)
        assert fetched is not None and fetched.id == first.id
        assert await memberships.count_active_owners(workspace_id=workspace.id) == 1

        with pytest.raises(IntegrityError):
            await memberships.create(
                user_id=user.id, workspace_id=workspace.id, role=Role.VIEWER, status=MembershipStatus.ACTIVE,
                invited_by=None, joined_at=_now(),
            )
    finally:
        await workspaces.update(workspace.id, changes={"is_active": False})
        await users.set_active(user.id, is_active=False)


@pytest.mark.asyncio
async def test_postgres_invitation_store_blocks_a_second_pending_invitation(stores) -> None:
    """Backed by the partial unique index (accepted_at/revoked_at both NULL),
    not just a service-level check.
    """

    _, workspaces, _, invitations = stores
    workspace = await workspaces.create(
        name="Acme", slug=f"postgres-test-{uuid4()}", logo_ref=None, default_timezone="UTC",
        default_locale="en-US", default_currency="USD",
    )
    email = f"invitee-{uuid4()}@example.com"

    try:
        first_token = generate_token()
        first = await invitations.create(
            workspace_id=workspace.id, email=email, role=Role.VIEWER, token_hash=hash_token(first_token),
            invited_by=None, expires_at=_now() + timedelta(days=7),
        )
        pending = await invitations.get_pending(workspace_id=workspace.id, email=email)
        assert pending is not None and pending.id == first.id

        with pytest.raises(IntegrityError):
            await invitations.create(
                workspace_id=workspace.id, email=email, role=Role.ANALYST, token_hash=hash_token(generate_token()),
                invited_by=None, expires_at=_now() + timedelta(days=7),
            )

        # Accepting the first invitation frees the (workspace, email) pair up again.
        await invitations.mark_accepted(first.id, at=_now())
        second_token = generate_token()
        second = await invitations.create(
            workspace_id=workspace.id, email=email, role=Role.ANALYST, token_hash=hash_token(second_token),
            invited_by=None, expires_at=_now() + timedelta(days=7),
        )
        assert second.id != first.id
    finally:
        await workspaces.update(workspace.id, changes={"is_active": False})
