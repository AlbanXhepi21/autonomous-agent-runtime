"""TenancyService behavior over in-memory tenancy storage: lifecycle rules,
context resolution, and every listed protection rule.

No PostgreSQL, no HTTP involved -- this exercises the service directly
against ``InMemoryWorkspaceStore``/``InMemoryMembershipStore``/
``InMemoryInvitationStore``, mirroring ``tests/unit/identity/test_service.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.audit.store import InMemoryAuditLogStore
from app.identity.contracts import User
from app.identity.email import FileEmailSender
from app.identity.tokens import generate_token, hash_token
from app.tenancy.contracts import MembershipStatus, ReportPreferences, Role, Workspace
from app.tenancy.service import (
    AdminCannotManageOwnerError,
    DuplicateInvitationError,
    DuplicateMembershipError,
    InvitationEmailMismatchError,
    InvitationInvalidError,
    LastOwnerError,
    MembershipDisabledError,
    MembershipNotFoundError,
    OwnerRequiredError,
    SlugAlreadyExistsError,
    TenancyService,
    WorkspaceInactiveError,
    WorkspaceNotFoundError,
)
from app.tenancy.store import (
    InMemoryInvitationStore,
    InMemoryMembershipStore,
    InMemoryWorkspaceStore,
    ReportPreferencesVersionConflictError,
    WorkspaceVersionConflictError,
)


def make_service(tmp_path: Path, **overrides) -> TenancyService:
    defaults = dict(
        workspaces=InMemoryWorkspaceStore(), memberships=InMemoryMembershipStore(),
        invitations=InMemoryInvitationStore(), email_sender=FileEmailSender(tmp_path / ".dev-mail"),
        invitation_ttl_seconds=604_800, app_base_url="http://localhost:3000",
    )
    defaults.update(overrides)
    return TenancyService(**defaults)


def make_user(email: str = "ada@example.com", **overrides) -> User:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid4(), email=email, display_name="Ada", password_hash="argon2-hash-placeholder",
        is_active=True, email_verified=False, created_at=now, updated_at=now, last_login_at=None,
    )
    defaults.update(overrides)
    return User(**defaults)


# -- create workspace -----------------------------------------------------


@pytest.mark.asyncio
async def test_create_workspace_makes_the_creator_an_owner(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    owner = make_user()

    workspace, membership = await service.create_workspace(name="Acme", slug="Acme Corp ", owner_user_id=owner.id)

    assert workspace.name == "Acme"
    assert workspace.slug == "acme corp"  # normalized: stripped + lowercased
    assert workspace.is_active is True
    assert membership.role is Role.OWNER
    assert membership.status is MembershipStatus.ACTIVE
    assert membership.invited_by is None
    assert membership.joined_at is not None


@pytest.mark.asyncio
async def test_create_workspace_rejects_a_duplicate_slug(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    await service.create_workspace(name="Acme", slug="acme", owner_user_id=uuid4())

    with pytest.raises(SlugAlreadyExistsError):
        await service.create_workspace(name="Acme Two", slug="ACME", owner_user_id=uuid4())


@pytest.mark.asyncio
async def test_update_settings_applies_a_partial_change(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    owner_id = uuid4()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner_id)

    updated = await service.update_settings(
        workspace_id=workspace.id, expected_version=workspace.version, changes={"default_currency": "EUR"},
        actor_user_id=owner_id,
    )

    assert updated.default_currency == "EUR"
    assert updated.name == "Acme"  # untouched
    assert updated.version == workspace.version + 1


# -- tenant context resolution ---------------------------------------------


@pytest.mark.asyncio
async def test_get_context_resolves_user_workspace_membership_role_and_permissions(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    owner = make_user()
    workspace, membership = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)

    context = await service.get_context(user=owner, workspace_id=workspace.id)

    assert context.user.id == owner.id
    assert context.workspace.id == workspace.id
    assert context.membership.id == membership.id
    assert context.role is Role.OWNER
    assert context.permissions == frozenset(context.permissions) and len(context.permissions) == 8
    assert context.has_permission(list(context.permissions)[0])


@pytest.mark.asyncio
async def test_get_context_rejects_an_unknown_workspace(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    with pytest.raises(WorkspaceNotFoundError):
        await service.get_context(user=make_user(), workspace_id=uuid4())


@pytest.mark.asyncio
async def test_get_context_rejects_an_inactive_workspace(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    await service.deactivate_workspace(workspace_id=workspace.id, acting_role=Role.OWNER, acting_user_id=owner.id)

    with pytest.raises(WorkspaceInactiveError):
        await service.get_context(user=owner, workspace_id=workspace.id)


@pytest.mark.asyncio
async def test_get_context_rejects_a_user_with_no_membership(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=uuid4())

    with pytest.raises(MembershipNotFoundError):
        await service.get_context(user=make_user(), workspace_id=workspace.id)


@pytest.mark.asyncio
async def test_get_context_rejects_a_disabled_membership(tmp_path: Path) -> None:
    memberships = InMemoryMembershipStore()
    service = make_service(tmp_path, memberships=memberships)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    viewer = make_user(email="viewer@example.com")
    membership = await memberships.create(
        user_id=viewer.id, workspace_id=workspace.id, role=Role.VIEWER, status=MembershipStatus.ACTIVE,
        invited_by=owner.id, joined_at=datetime.now(UTC),
    )
    await memberships.update_status(membership.id, status=MembershipStatus.DISABLED)

    with pytest.raises(MembershipDisabledError):
        await service.get_context(user=viewer, workspace_id=workspace.id)


# -- invitations ------------------------------------------------------------


@pytest.mark.asyncio
async def test_invite_member_sends_exactly_one_email(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)

    invitation = await service.invite_member(
        workspace_id=workspace.id, email="Analyst@Example.COM", role=Role.ANALYST,
        invited_by_user_id=owner.id, inviter_role=Role.OWNER,
    )

    assert invitation.email == "analyst@example.com"  # normalized
    assert invitation.accepted_at is None and invitation.revoked_at is None
    assert len(sender.sent) == 1
    assert sender.sent[0].to == "analyst@example.com"
    assert "invited" in sender.sent[0].subject.lower()


@pytest.mark.asyncio
async def test_invite_member_rejects_a_duplicate_pending_invitation(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    await service.invite_member(
        workspace_id=workspace.id, email="analyst@example.com", role=Role.ANALYST,
        invited_by_user_id=owner.id, inviter_role=Role.OWNER,
    )

    with pytest.raises(DuplicateInvitationError):
        await service.invite_member(
            workspace_id=workspace.id, email="ANALYST@example.com", role=Role.VIEWER,
            invited_by_user_id=owner.id, inviter_role=Role.OWNER,
        )


@pytest.mark.asyncio
async def test_invite_member_as_owner_requires_an_owner_actor(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)

    with pytest.raises(AdminCannotManageOwnerError):
        await service.invite_member(
            workspace_id=workspace.id, email="new-owner@example.com", role=Role.OWNER,
            invited_by_user_id=uuid4(), inviter_role=Role.ADMIN,
        )


@pytest.mark.asyncio
async def test_accept_invitation_creates_an_active_membership(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    await service.invite_member(
        workspace_id=workspace.id, email="analyst@example.com", role=Role.ANALYST,
        invited_by_user_id=owner.id, inviter_role=Role.OWNER,
    )
    token = _extract_token(sender.sent[-1].body)
    invitee = make_user(email="analyst@example.com")

    membership = await service.accept_invitation(token=token, accepting_user=invitee)

    assert membership.user_id == invitee.id
    assert membership.role is Role.ANALYST
    assert membership.status is MembershipStatus.ACTIVE
    assert membership.invited_by == owner.id
    assert membership.joined_at is not None


@pytest.mark.asyncio
async def test_accept_invitation_is_single_use(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    await service.invite_member(
        workspace_id=workspace.id, email="analyst@example.com", role=Role.ANALYST,
        invited_by_user_id=owner.id, inviter_role=Role.OWNER,
    )
    token = _extract_token(sender.sent[-1].body)
    first_invitee = make_user(email="analyst@example.com")
    await service.accept_invitation(token=token, accepting_user=first_invitee)

    second_invitee = make_user(email="analyst@example.com")
    with pytest.raises(InvitationInvalidError):
        await service.accept_invitation(token=token, accepting_user=second_invitee)


@pytest.mark.asyncio
async def test_accept_invitation_rejects_an_expired_invitation(tmp_path: Path) -> None:
    """An invitation created with an already-past `expires_at` -- the same
    shape a real one takes once its TTL elapses -- is refused.
    """

    invitations = InMemoryInvitationStore()
    service = make_service(tmp_path, invitations=invitations)
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=uuid4())
    raw_token = generate_token()
    await invitations.create(
        workspace_id=workspace.id, email="analyst@example.com", role=Role.ANALYST, token_hash=hash_token(raw_token),
        invited_by=None, expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    with pytest.raises(InvitationInvalidError):
        await service.accept_invitation(token=raw_token, accepting_user=make_user(email="analyst@example.com"))


@pytest.mark.asyncio
async def test_accept_invitation_rejects_an_unknown_token(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    with pytest.raises(InvitationInvalidError):
        await service.accept_invitation(token="not-a-real-token", accepting_user=make_user())


@pytest.mark.asyncio
async def test_accept_invitation_rejects_a_mismatched_email(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    service = make_service(tmp_path, email_sender=sender)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    await service.invite_member(
        workspace_id=workspace.id, email="intended@example.com", role=Role.ANALYST,
        invited_by_user_id=owner.id, inviter_role=Role.OWNER,
    )
    token = _extract_token(sender.sent[-1].body)
    wrong_person = make_user(email="someone-else@example.com")

    with pytest.raises(InvitationEmailMismatchError):
        await service.accept_invitation(token=token, accepting_user=wrong_person)


@pytest.mark.asyncio
async def test_accept_invitation_rejects_when_already_a_member(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path / ".dev-mail")
    memberships = InMemoryMembershipStore()
    service = make_service(tmp_path, email_sender=sender, memberships=memberships)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    existing_member = make_user(email="already-here@example.com")
    await memberships.create(
        user_id=existing_member.id, workspace_id=workspace.id, role=Role.VIEWER, status=MembershipStatus.ACTIVE,
        invited_by=owner.id, joined_at=datetime.now(UTC),
    )
    await service.invite_member(
        workspace_id=workspace.id, email="already-here@example.com", role=Role.ANALYST,
        invited_by_user_id=owner.id, inviter_role=Role.OWNER,
    )
    token = _extract_token(sender.sent[-1].body)

    with pytest.raises(DuplicateMembershipError):
        await service.accept_invitation(token=token, accepting_user=existing_member)


# -- change role -------------------------------------------------------------


@pytest.mark.asyncio
async def test_change_role_updates_the_role(tmp_path: Path) -> None:
    memberships = InMemoryMembershipStore()
    service = make_service(tmp_path, memberships=memberships)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    analyst = make_user(email="analyst@example.com")
    await memberships.create(
        user_id=analyst.id, workspace_id=workspace.id, role=Role.ANALYST, status=MembershipStatus.ACTIVE,
        invited_by=owner.id, joined_at=datetime.now(UTC),
    )

    updated = await service.change_role(
        workspace_id=workspace.id, target_user_id=analyst.id, new_role=Role.ADMIN, acting_role=Role.OWNER,
        acting_user_id=owner.id,
    )

    assert updated.role is Role.ADMIN


@pytest.mark.asyncio
async def test_change_role_admin_cannot_promote_anyone_to_owner(tmp_path: Path) -> None:
    memberships = InMemoryMembershipStore()
    service = make_service(tmp_path, memberships=memberships)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    analyst = make_user(email="analyst@example.com")
    await memberships.create(
        user_id=analyst.id, workspace_id=workspace.id, role=Role.ANALYST, status=MembershipStatus.ACTIVE,
        invited_by=owner.id, joined_at=datetime.now(UTC),
    )

    with pytest.raises(AdminCannotManageOwnerError):
        await service.change_role(
            workspace_id=workspace.id, target_user_id=analyst.id, new_role=Role.OWNER, acting_role=Role.ADMIN,
            acting_user_id=owner.id,
        )


@pytest.mark.asyncio
async def test_change_role_admin_cannot_demote_an_owner(tmp_path: Path) -> None:
    memberships = InMemoryMembershipStore()
    service = make_service(tmp_path, memberships=memberships)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    second_owner = make_user(email="second-owner@example.com")
    await memberships.create(
        user_id=second_owner.id, workspace_id=workspace.id, role=Role.OWNER, status=MembershipStatus.ACTIVE,
        invited_by=owner.id, joined_at=datetime.now(UTC),
    )

    with pytest.raises(AdminCannotManageOwnerError):
        await service.change_role(
            workspace_id=workspace.id, target_user_id=second_owner.id, new_role=Role.ADMIN, acting_role=Role.ADMIN,
            acting_user_id=owner.id,
        )


@pytest.mark.asyncio
async def test_change_role_cannot_demote_the_last_owner_even_by_another_owner(tmp_path: Path) -> None:
    """There is only one owner, so demoting them -- regardless of who asks -- is refused."""

    service = make_service(tmp_path)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)

    with pytest.raises(LastOwnerError):
        await service.change_role(
            workspace_id=workspace.id, target_user_id=owner.id, new_role=Role.ADMIN, acting_role=Role.OWNER,
            acting_user_id=owner.id,
        )


@pytest.mark.asyncio
async def test_change_role_permits_demoting_one_of_two_owners(tmp_path: Path) -> None:
    memberships = InMemoryMembershipStore()
    service = make_service(tmp_path, memberships=memberships)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    second_owner = make_user(email="second-owner@example.com")
    await memberships.create(
        user_id=second_owner.id, workspace_id=workspace.id, role=Role.OWNER, status=MembershipStatus.ACTIVE,
        invited_by=owner.id, joined_at=datetime.now(UTC),
    )

    updated = await service.change_role(
        workspace_id=workspace.id, target_user_id=second_owner.id, new_role=Role.ADMIN, acting_role=Role.OWNER,
        acting_user_id=owner.id,
    )

    assert updated.role is Role.ADMIN


@pytest.mark.asyncio
async def test_change_role_rejects_an_unknown_member(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    owner_id = uuid4()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner_id)

    with pytest.raises(MembershipNotFoundError):
        await service.change_role(
            workspace_id=workspace.id, target_user_id=uuid4(), new_role=Role.ADMIN, acting_role=Role.OWNER,
            acting_user_id=owner_id,
        )


# -- remove member -----------------------------------------------------------


@pytest.mark.asyncio
async def test_remove_member_disables_rather_than_deletes(tmp_path: Path) -> None:
    memberships = InMemoryMembershipStore()
    service = make_service(tmp_path, memberships=memberships)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    viewer = make_user(email="viewer@example.com")
    await memberships.create(
        user_id=viewer.id, workspace_id=workspace.id, role=Role.VIEWER, status=MembershipStatus.ACTIVE,
        invited_by=owner.id, joined_at=datetime.now(UTC),
    )

    updated = await service.remove_member(
        workspace_id=workspace.id, target_user_id=viewer.id, acting_role=Role.OWNER, acting_user_id=owner.id,
    )

    assert updated.status is MembershipStatus.DISABLED
    still_present = await memberships.get_for_user(workspace_id=workspace.id, user_id=viewer.id)
    assert still_present is not None  # soft removal: the row still exists


@pytest.mark.asyncio
async def test_remove_member_admin_cannot_remove_an_owner(tmp_path: Path) -> None:
    memberships = InMemoryMembershipStore()
    service = make_service(tmp_path, memberships=memberships)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    second_owner = make_user(email="second-owner@example.com")
    await memberships.create(
        user_id=second_owner.id, workspace_id=workspace.id, role=Role.OWNER, status=MembershipStatus.ACTIVE,
        invited_by=owner.id, joined_at=datetime.now(UTC),
    )

    with pytest.raises(AdminCannotManageOwnerError):
        await service.remove_member(
            workspace_id=workspace.id, target_user_id=second_owner.id, acting_role=Role.ADMIN,
            acting_user_id=owner.id,
        )


@pytest.mark.asyncio
async def test_remove_member_cannot_remove_the_last_owner(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)

    with pytest.raises(LastOwnerError):
        await service.remove_member(
            workspace_id=workspace.id, target_user_id=owner.id, acting_role=Role.OWNER, acting_user_id=owner.id,
        )


@pytest.mark.asyncio
async def test_remove_member_rejects_an_unknown_member(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    owner_id = uuid4()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner_id)

    with pytest.raises(MembershipNotFoundError):
        await service.remove_member(
            workspace_id=workspace.id, target_user_id=uuid4(), acting_role=Role.OWNER, acting_user_id=owner_id,
        )


# -- leave workspace -----------------------------------------------------------


@pytest.mark.asyncio
async def test_leave_workspace_disables_the_membership(tmp_path: Path) -> None:
    memberships = InMemoryMembershipStore()
    service = make_service(tmp_path, memberships=memberships)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    viewer = make_user(email="viewer@example.com")
    await memberships.create(
        user_id=viewer.id, workspace_id=workspace.id, role=Role.VIEWER, status=MembershipStatus.ACTIVE,
        invited_by=owner.id, joined_at=datetime.now(UTC),
    )

    updated = await service.leave_workspace(workspace_id=workspace.id, user_id=viewer.id)

    assert updated.status is MembershipStatus.DISABLED


@pytest.mark.asyncio
async def test_the_last_owner_cannot_leave(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)

    with pytest.raises(LastOwnerError):
        await service.leave_workspace(workspace_id=workspace.id, user_id=owner.id)


@pytest.mark.asyncio
async def test_one_of_two_owners_can_leave(tmp_path: Path) -> None:
    memberships = InMemoryMembershipStore()
    service = make_service(tmp_path, memberships=memberships)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    second_owner = make_user(email="second-owner@example.com")
    await memberships.create(
        user_id=second_owner.id, workspace_id=workspace.id, role=Role.OWNER, status=MembershipStatus.ACTIVE,
        invited_by=owner.id, joined_at=datetime.now(UTC),
    )

    updated = await service.leave_workspace(workspace_id=workspace.id, user_id=owner.id)

    assert updated.status is MembershipStatus.DISABLED


# -- transfer ownership ---------------------------------------------------------


@pytest.mark.asyncio
async def test_transfer_ownership_promotes_target_and_demotes_source(tmp_path: Path) -> None:
    memberships = InMemoryMembershipStore()
    service = make_service(tmp_path, memberships=memberships)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    admin = make_user(email="admin@example.com")
    await memberships.create(
        user_id=admin.id, workspace_id=workspace.id, role=Role.ADMIN, status=MembershipStatus.ACTIVE,
        invited_by=owner.id, joined_at=datetime.now(UTC),
    )

    updated_target = await service.transfer_ownership(
        workspace_id=workspace.id, from_user_id=owner.id, to_user_id=admin.id, acting_role=Role.OWNER,
    )

    assert updated_target.role is Role.OWNER
    former_owner = await memberships.get_for_user(workspace_id=workspace.id, user_id=owner.id)
    assert former_owner is not None and former_owner.role is Role.ADMIN


@pytest.mark.asyncio
async def test_transfer_ownership_requires_an_owner_actor(tmp_path: Path) -> None:
    memberships = InMemoryMembershipStore()
    service = make_service(tmp_path, memberships=memberships)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    admin = make_user(email="admin@example.com")
    await memberships.create(
        user_id=admin.id, workspace_id=workspace.id, role=Role.ADMIN, status=MembershipStatus.ACTIVE,
        invited_by=owner.id, joined_at=datetime.now(UTC),
    )

    with pytest.raises(OwnerRequiredError):
        await service.transfer_ownership(
            workspace_id=workspace.id, from_user_id=admin.id, to_user_id=owner.id, acting_role=Role.ADMIN,
        )


@pytest.mark.asyncio
async def test_transfer_ownership_target_must_be_an_active_member(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)

    with pytest.raises(MembershipNotFoundError):
        await service.transfer_ownership(
            workspace_id=workspace.id, from_user_id=owner.id, to_user_id=uuid4(), acting_role=Role.OWNER,
        )


# -- deactivate workspace --------------------------------------------------------


@pytest.mark.asyncio
async def test_deactivate_workspace_requires_an_owner(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    owner_id = uuid4()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner_id)

    with pytest.raises(OwnerRequiredError):
        await service.deactivate_workspace(workspace_id=workspace.id, acting_role=Role.ADMIN, acting_user_id=owner_id)


@pytest.mark.asyncio
async def test_deactivate_workspace_marks_it_inactive_and_blocks_new_context_resolution(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)

    deactivated = await service.deactivate_workspace(
        workspace_id=workspace.id, acting_role=Role.OWNER, acting_user_id=owner.id,
    )

    assert deactivated.is_active is False
    with pytest.raises(WorkspaceInactiveError):
        await service.get_context(user=owner, workspace_id=workspace.id)


def _extract_token(body: str) -> str:
    line = next(line for line in body.splitlines() if "token=" in line)
    return line.rsplit("token=", 1)[-1].strip()


# -- workspace settings validation (contract-level) ---------------------------


def _workspace(**overrides) -> Workspace:
    now = datetime.now(UTC)
    fields = dict(
        id=uuid4(), name="Acme", slug="acme", is_active=True, default_timezone="UTC",
        default_locale="en-US", default_currency="USD", created_at=now, updated_at=now,
    )
    fields.update(overrides)
    return Workspace(**fields)


def test_workspace_rejects_an_unknown_timezone() -> None:
    with pytest.raises(ValidationError, match="Unknown IANA timezone"):
        _workspace(default_timezone="Mars/Olympus_Mons")


def test_workspace_accepts_a_known_timezone() -> None:
    assert _workspace(default_timezone="America/New_York").default_timezone == "America/New_York"


def test_workspace_rejects_an_unknown_currency() -> None:
    with pytest.raises(ValidationError, match="Unknown ISO 4217 currency"):
        _workspace(default_currency="ZZZ")


def test_workspace_accepts_a_known_currency() -> None:
    assert _workspace(default_currency="jpy").default_currency == "JPY"  # normalized to uppercase


def test_workspace_rejects_a_malformed_locale() -> None:
    with pytest.raises(ValidationError, match="Invalid locale tag"):
        _workspace(default_locale="not_a_locale!!")


def test_workspace_accepts_a_well_formed_locale() -> None:
    assert _workspace(default_locale="pt-BR").default_locale == "pt-BR"


def test_workspace_rejects_a_fiscal_year_start_month_outside_1_to_12() -> None:
    with pytest.raises(ValidationError):
        _workspace(fiscal_year_start_month=13)


# -- workspace settings: optimistic concurrency --------------------------------


@pytest.mark.asyncio
async def test_update_settings_rejects_a_stale_expected_version(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    await service.update_settings(
        workspace_id=workspace.id, expected_version=workspace.version, changes={"name": "Acme Renamed"},
        actor_user_id=owner.id,
    )

    with pytest.raises(WorkspaceVersionConflictError):
        await service.update_settings(
            workspace_id=workspace.id, expected_version=workspace.version, changes={"name": "Acme Again"},
            actor_user_id=owner.id,
        )


@pytest.mark.asyncio
async def test_update_settings_is_recorded_in_the_audit_log(tmp_path: Path) -> None:
    audit = InMemoryAuditLogStore()
    service = make_service(tmp_path, audit=audit)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)

    await service.update_settings(
        workspace_id=workspace.id, expected_version=workspace.version, changes={"default_currency": "EUR"},
        actor_user_id=owner.id,
    )

    entries = await audit.list_for_workspace(workspace_id=workspace.id)
    assert [entry.event_type for entry in entries] == ["tenancy_workspace_settings_updated"]
    assert entries[0].actor_user_id == owner.id
    assert entries[0].metadata["changed_fields"] == ["default_currency"]


@pytest.mark.asyncio
async def test_role_change_removal_and_deactivation_are_all_recorded_in_the_audit_log(tmp_path: Path) -> None:
    audit = InMemoryAuditLogStore()
    memberships = InMemoryMembershipStore()
    service = make_service(tmp_path, memberships=memberships, audit=audit)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    analyst = make_user(email="analyst@example.com")
    await memberships.create(
        user_id=analyst.id, workspace_id=workspace.id, role=Role.ANALYST, status=MembershipStatus.ACTIVE,
        invited_by=owner.id, joined_at=datetime.now(UTC),
    )

    await service.change_role(
        workspace_id=workspace.id, target_user_id=analyst.id, new_role=Role.ADMIN, acting_role=Role.OWNER,
        acting_user_id=owner.id,
    )
    await service.remove_member(
        workspace_id=workspace.id, target_user_id=analyst.id, acting_role=Role.OWNER, acting_user_id=owner.id,
    )
    await service.deactivate_workspace(workspace_id=workspace.id, acting_role=Role.OWNER, acting_user_id=owner.id)

    entries = await audit.list_for_workspace(workspace_id=workspace.id)
    event_types = {entry.event_type for entry in entries}
    assert {"tenancy_role_changed", "tenancy_member_removed", "tenancy_workspace_deactivated"} <= event_types
    assert all(entry.actor_user_id == owner.id for entry in entries)


# -- report preferences ---------------------------------------------------------


@pytest.mark.asyncio
async def test_get_report_preferences_creates_an_all_defaults_row(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)

    preferences = await service.get_report_preferences(workspace_id=workspace.id)

    assert preferences.workspace_id == workspace.id
    assert preferences.default_template is None
    assert preferences.evidence_appendix_enabled is True
    assert preferences.technical_sql_appendix_enabled is False
    assert preferences.version == 1


@pytest.mark.asyncio
async def test_update_report_preferences_applies_a_partial_change(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    preferences = await service.get_report_preferences(workspace_id=workspace.id)

    updated = await service.update_report_preferences(
        workspace_id=workspace.id, expected_version=preferences.version,
        changes={"default_template": "monthly_business_review", "default_output_format": "pdf"},
        actor_user_id=owner.id,
    )

    assert updated.default_template == "monthly_business_review"
    assert updated.default_output_format == "pdf"
    assert updated.evidence_appendix_enabled is True  # untouched
    assert updated.version == preferences.version + 1


@pytest.mark.asyncio
async def test_update_report_preferences_rejects_a_stale_expected_version(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    preferences = await service.get_report_preferences(workspace_id=workspace.id)
    await service.update_report_preferences(
        workspace_id=workspace.id, expected_version=preferences.version,
        changes={"default_theme": "dark"}, actor_user_id=owner.id,
    )

    with pytest.raises(ReportPreferencesVersionConflictError):
        await service.update_report_preferences(
            workspace_id=workspace.id, expected_version=preferences.version,
            changes={"default_theme": "light"}, actor_user_id=owner.id,
        )


@pytest.mark.asyncio
async def test_update_report_preferences_is_recorded_in_the_audit_log(tmp_path: Path) -> None:
    audit = InMemoryAuditLogStore()
    service = make_service(tmp_path, audit=audit)
    owner = make_user()
    workspace, _ = await service.create_workspace(name="Acme", slug="acme", owner_user_id=owner.id)
    preferences = await service.get_report_preferences(workspace_id=workspace.id)

    await service.update_report_preferences(
        workspace_id=workspace.id, expected_version=preferences.version,
        changes={"evidence_appendix_enabled": False}, actor_user_id=owner.id,
    )

    entries = await audit.list_for_workspace(workspace_id=workspace.id)
    assert "tenancy_report_preferences_updated" in {entry.event_type for entry in entries}


def test_report_preferences_settings_never_carry_a_narrative_that_changes_facts() -> None:
    """Every field is presentation-only -- there is no field here that could
    alter what a report states, only how it is assembled and formatted.
    """

    fields = set(ReportPreferences.model_fields) - {
        "workspace_id", "version", "created_at", "updated_at",
    }
    assert fields == {
        "default_template", "default_output_format", "default_theme",
        "default_narrative_policy", "evidence_appendix_enabled", "technical_sql_appendix_enabled",
    }
