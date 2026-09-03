"""Workspace and membership lifecycle behavior over tenancy storage.

Everything HTTP-shaped lives in ``app.api``; this module only knows about
workspaces, memberships, and invitations. Role-name comparisons live in
exactly the handful of places below (never in a route) -- see each method's
docstring for which lifecycle rule it enforces.

No reactivation flow exists in this phase: ``remove_member`` and
``leave_workspace`` disable a membership rather than delete it (preserving
who was invited by whom and when they joined), but ``accept_invitation``
treats any existing membership row -- active or disabled -- as a duplicate.
Rejoining after removal is out of scope here.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.audit.contracts import AuditLogEntry
from app.audit.store import AuditLogStore, InMemoryAuditLogStore
from app.core.logging import log_event
from app.identity.contracts import User
from app.identity.email import EmailMessage, EmailSender
from app.identity.tokens import generate_token, hash_token
from app.tenancy.context import TenantContext
from app.tenancy.contracts import Invitation, Membership, MembershipStatus, ReportPreferences, Role, Workspace
from app.tenancy.permissions import permissions_for_role
from app.tenancy.store import (
    InMemoryReportPreferencesStore,
    InvitationStore,
    MembershipStore,
    ReportPreferencesStore,
    WorkspaceStore,
)

_logger = logging.getLogger(__name__)


class TenancyError(Exception):
    """Base class for tenancy-domain failures the API layer must translate."""


class SlugAlreadyExistsError(TenancyError):
    pass


class WorkspaceNotFoundError(TenancyError):
    pass


class WorkspaceInactiveError(TenancyError):
    pass


class MembershipNotFoundError(TenancyError):
    pass


class MembershipDisabledError(TenancyError):
    pass


class DuplicateMembershipError(TenancyError):
    pass


class DuplicateInvitationError(TenancyError):
    pass


class InvitationInvalidError(TenancyError):
    pass


class InvitationEmailMismatchError(TenancyError):
    pass


class LastOwnerError(TenancyError):
    """Every active workspace must retain at least one owner."""


class AdminCannotManageOwnerError(TenancyError):
    """An actor who is not themselves an owner tried to affect an owner-level membership."""


class OwnerRequiredError(TenancyError):
    """The action requires the actor to be an owner, independent of any target."""


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_slug(slug: str) -> str:
    return slug.strip().lower()


def _now() -> datetime:
    return datetime.now(UTC)


def _invitation_is_pending(invitation: Invitation, *, now: datetime) -> bool:
    return invitation.accepted_at is None and invitation.revoked_at is None and invitation.expires_at >= now


class TenancyService:
    def __init__(
        self, *, workspaces: WorkspaceStore, memberships: MembershipStore, invitations: InvitationStore,
        email_sender: EmailSender, invitation_ttl_seconds: int, app_base_url: str,
        report_preferences: ReportPreferencesStore | None = None, audit: AuditLogStore | None = None,
    ) -> None:
        self._workspaces = workspaces
        self._memberships = memberships
        self._invitations = invitations
        self._email = email_sender
        self._invitation_ttl = timedelta(seconds=invitation_ttl_seconds)
        self._app_base_url = app_base_url.rstrip("/")
        # Both optional so every existing call site (this service is
        # constructed directly across most of the test suite) keeps working
        # unchanged -- see ``AuthService.__init__`` for the same reasoning.
        self._report_preferences = report_preferences or InMemoryReportPreferencesStore()
        self._audit = audit or InMemoryAuditLogStore()

    # -- tenant context: the one authoritative resolver ------------------------

    async def get_context(self, *, user: User, workspace_id: UUID) -> TenantContext:
        """Every tenant-scoped request resolves through here.

        Raises, in order: ``WorkspaceNotFoundError``, ``WorkspaceInactiveError``
        (an inactive workspace cannot be used, regardless of membership),
        ``MembershipNotFoundError`` (the user has never belonged to this
        workspace), ``MembershipDisabledError`` (they did, but were removed
        or left).
        """

        workspace = await self._workspaces.get(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(str(workspace_id))
        if not workspace.is_active:
            raise WorkspaceInactiveError(str(workspace_id))
        membership = await self._memberships.get_for_user(workspace_id=workspace_id, user_id=user.id)
        if membership is None:
            raise MembershipNotFoundError(str(user.id))
        if membership.status is not MembershipStatus.ACTIVE:
            raise MembershipDisabledError(str(membership.id))
        return TenantContext(
            user=user, workspace=workspace, membership=membership, role=membership.role,
            permissions=permissions_for_role(membership.role),
        )

    # -- create ------------------------------------------------------------

    async def create_workspace(
        self, *, name: str, slug: str, owner_user_id: UUID, logo_ref: str | None = None,
        default_timezone: str = "UTC", default_locale: str = "en-US", default_currency: str = "USD",
    ) -> tuple[Workspace, Membership]:
        """Tenant creation makes the creating user an owner."""

        normalized_slug = normalize_slug(slug)
        if await self._workspaces.get_by_slug(normalized_slug) is not None:
            raise SlugAlreadyExistsError(normalized_slug)
        workspace = await self._workspaces.create(
            name=name.strip(), slug=normalized_slug, logo_ref=logo_ref, default_timezone=default_timezone,
            default_locale=default_locale, default_currency=default_currency,
        )
        membership = await self._memberships.create(
            user_id=owner_user_id, workspace_id=workspace.id, role=Role.OWNER, status=MembershipStatus.ACTIVE,
            invited_by=None, joined_at=_now(),
        )
        log_event(
            _logger, logging.INFO, "tenancy_workspace_created",
            workspace_id=str(workspace.id), slug=workspace.slug, owner_user_id=str(owner_user_id),
        )
        return workspace, membership

    async def update_settings(
        self, *, workspace_id: UUID, expected_version: int, changes: dict[str, object], actor_user_id: UUID,
    ) -> Workspace:
        """Raises ``WorkspaceVersionConflictError`` (from ``app.tenancy.store``)
        when ``expected_version`` no longer matches the stored row.
        """

        workspace = await self._workspaces.update(workspace_id, changes=changes, expected_version=expected_version)
        if workspace is None:
            raise WorkspaceNotFoundError(str(workspace_id))
        log_event(_logger, logging.INFO, "tenancy_workspace_settings_updated", workspace_id=str(workspace_id))
        await self._audit.record(
            actor_user_id=actor_user_id, workspace_id=workspace_id, event_type="tenancy_workspace_settings_updated",
            metadata={"changed_fields": sorted(changes)},
        )
        return workspace

    # -- report preferences --------------------------------------------------

    async def get_report_preferences(self, *, workspace_id: UUID) -> ReportPreferences:
        return await self._report_preferences.get_or_create(workspace_id=workspace_id)

    async def update_report_preferences(
        self, *, workspace_id: UUID, expected_version: int, changes: dict[str, object], actor_user_id: UUID,
    ) -> ReportPreferences:
        """Raises ``ReportPreferencesVersionConflictError`` (from
        ``app.tenancy.store``) when ``expected_version`` no longer matches.
        Settings here change presentation only -- never a report's figures.
        """

        updated = await self._report_preferences.update(
            workspace_id=workspace_id, expected_version=expected_version, changes=changes,
        )
        log_event(_logger, logging.INFO, "tenancy_report_preferences_updated", workspace_id=str(workspace_id))
        await self._audit.record(
            actor_user_id=actor_user_id, workspace_id=workspace_id,
            event_type="tenancy_report_preferences_updated", metadata={"changed_fields": sorted(changes)},
        )
        return updated

    # -- membership lifecycle ------------------------------------------------

    async def invite_member(
        self, *, workspace_id: UUID, email: str, role: Role, invited_by_user_id: UUID, inviter_role: Role,
    ) -> Invitation:
        """Invitations are expiring, single-use, and bound to a normalized email + this workspace.

        Only an owner may invite a new owner -- the same "admins cannot
        manage owners" rule ``change_role``/``remove_member`` enforce,
        extended to "an admin cannot create one either."
        """

        workspace = await self._require_active_workspace(workspace_id)
        if role is Role.OWNER and inviter_role is not Role.OWNER:
            raise AdminCannotManageOwnerError("Only an owner may invite a new owner.")
        normalized_email = normalize_email(email)
        if await self._invitations.get_pending(workspace_id=workspace_id, email=normalized_email) is not None:
            raise DuplicateInvitationError(normalized_email)

        raw_token = generate_token()
        invitation = await self._invitations.create(
            workspace_id=workspace_id, email=normalized_email, role=role, token_hash=hash_token(raw_token),
            invited_by=invited_by_user_id, expires_at=_now() + self._invitation_ttl,
        )
        await self._email.send(self._compose_invite_message(workspace=workspace, email=normalized_email, raw_token=raw_token))
        log_event(
            _logger, logging.INFO, "tenancy_member_invited",
            workspace_id=str(workspace_id), invitation_id=str(invitation.id), role=role.value,
        )
        await self._audit.record(
            actor_user_id=invited_by_user_id, workspace_id=workspace_id, event_type="tenancy_member_invited",
            metadata={"role": role.value},
        )
        return invitation

    async def accept_invitation(self, *, token: str, accepting_user: User) -> Membership:
        """Single-use: the invitation is marked accepted the same call that redeems it.

        Rejects a token whose invitation was sent to a different address
        than the accepting user's own -- an invitation is bound to an email,
        not whoever happens to hold the link.
        """

        invitation = await self._invitations.get_by_token_hash(hash_token(token))
        now = _now()
        if invitation is None or not _invitation_is_pending(invitation, now=now):
            raise InvitationInvalidError("This invitation is invalid or has expired.")
        if normalize_email(accepting_user.email) != invitation.email:
            raise InvitationEmailMismatchError("This invitation was sent to a different email address.")
        workspace = await self._workspaces.get(invitation.workspace_id)
        if workspace is None or not workspace.is_active:
            raise WorkspaceInactiveError(str(invitation.workspace_id))
        if await self._memberships.get_for_user(workspace_id=invitation.workspace_id, user_id=accepting_user.id) is not None:
            raise DuplicateMembershipError(str(accepting_user.id))

        membership = await self._memberships.create(
            user_id=accepting_user.id, workspace_id=invitation.workspace_id, role=invitation.role,
            status=MembershipStatus.ACTIVE, invited_by=invitation.invited_by, joined_at=now,
        )
        await self._invitations.mark_accepted(invitation.id, at=now)
        log_event(
            _logger, logging.INFO, "tenancy_invitation_accepted",
            workspace_id=str(invitation.workspace_id), user_id=str(accepting_user.id),
        )
        await self._audit.record(
            actor_user_id=accepting_user.id, workspace_id=invitation.workspace_id,
            event_type="tenancy_invitation_accepted", metadata={"role": invitation.role.value},
        )
        return membership

    async def change_role(
        self, *, workspace_id: UUID, target_user_id: UUID, new_role: Role, acting_role: Role, acting_user_id: UUID,
    ) -> Membership:
        """Admins cannot manage owners: neither demoting an existing owner nor
        promoting anyone to owner is permitted unless the actor is one.
        Demoting the last owner is refused outright, regardless of actor.
        """

        target = await self._memberships.get_for_user(workspace_id=workspace_id, user_id=target_user_id)
        if target is None:
            raise MembershipNotFoundError(str(target_user_id))
        if target.role is Role.OWNER and acting_role is not Role.OWNER:
            raise AdminCannotManageOwnerError("Only an owner may change another owner's role.")
        if new_role is Role.OWNER and acting_role is not Role.OWNER:
            raise AdminCannotManageOwnerError("Only an owner may grant the owner role.")
        demoting_the_only_owner = target.role is Role.OWNER and new_role is not Role.OWNER
        if demoting_the_only_owner and await self._memberships.count_active_owners(workspace_id=workspace_id) <= 1:
            raise LastOwnerError("A workspace must retain at least one owner.")

        updated = await self._memberships.update_role(target.id, role=new_role)
        assert updated is not None
        log_event(
            _logger, logging.INFO, "tenancy_role_changed",
            workspace_id=str(workspace_id), target_user_id=str(target_user_id), role=new_role.value,
        )
        await self._audit.record(
            actor_user_id=acting_user_id, workspace_id=workspace_id, event_type="tenancy_role_changed",
            metadata={"target_user_id": str(target_user_id), "role": new_role.value},
        )
        return updated

    async def remove_member(
        self, *, workspace_id: UUID, target_user_id: UUID, acting_role: Role, acting_user_id: UUID,
    ) -> Membership:
        """Soft-removal (status -> DISABLED), preserving membership history.
        The last owner cannot be removed, by anyone.
        """

        target = await self._memberships.get_for_user(workspace_id=workspace_id, user_id=target_user_id)
        if target is None:
            raise MembershipNotFoundError(str(target_user_id))
        if target.role is Role.OWNER:
            if acting_role is not Role.OWNER:
                raise AdminCannotManageOwnerError("Only an owner may remove another owner.")
            if await self._memberships.count_active_owners(workspace_id=workspace_id) <= 1:
                raise LastOwnerError("The last owner cannot be removed.")

        updated = await self._memberships.update_status(target.id, status=MembershipStatus.DISABLED)
        assert updated is not None
        log_event(_logger, logging.INFO, "tenancy_member_removed", workspace_id=str(workspace_id), target_user_id=str(target_user_id))
        await self._audit.record(
            actor_user_id=acting_user_id, workspace_id=workspace_id, event_type="tenancy_member_removed",
            metadata={"target_user_id": str(target_user_id)},
        )
        return updated

    async def leave_workspace(self, *, workspace_id: UUID, user_id: UUID) -> Membership:
        """The last owner cannot leave -- transfer ownership or promote another
        owner first.
        """

        membership = await self._memberships.get_for_user(workspace_id=workspace_id, user_id=user_id)
        if membership is None:
            raise MembershipNotFoundError(str(user_id))
        if membership.role is Role.OWNER and await self._memberships.count_active_owners(workspace_id=workspace_id) <= 1:
            raise LastOwnerError("The last owner cannot leave the workspace.")

        updated = await self._memberships.update_status(membership.id, status=MembershipStatus.DISABLED)
        assert updated is not None
        log_event(_logger, logging.INFO, "tenancy_member_left", workspace_id=str(workspace_id), user_id=str(user_id))
        return updated

    async def transfer_ownership(
        self, *, workspace_id: UUID, from_user_id: UUID, to_user_id: UUID, acting_role: Role,
    ) -> Membership:
        """Only an owner may transfer ownership. The recipient must already be
        an active member; transferring promotes them to owner and demotes
        the transferring owner to admin -- distinct from ``change_role``,
        which can freely add *additional* owners without touching the caller.
        """

        if acting_role is not Role.OWNER:
            raise OwnerRequiredError("Only an owner may transfer ownership.")
        from_membership = await self._memberships.get_for_user(workspace_id=workspace_id, user_id=from_user_id)
        if (
            from_membership is None or from_membership.role is not Role.OWNER
            or from_membership.status is not MembershipStatus.ACTIVE
        ):
            raise OwnerRequiredError("The acting user is not an active owner of this workspace.")
        to_membership = await self._memberships.get_for_user(workspace_id=workspace_id, user_id=to_user_id)
        if to_membership is None or to_membership.status is not MembershipStatus.ACTIVE:
            raise MembershipNotFoundError(str(to_user_id))

        updated_target = await self._memberships.update_role(to_membership.id, role=Role.OWNER)
        await self._memberships.update_role(from_membership.id, role=Role.ADMIN)
        assert updated_target is not None
        log_event(
            _logger, logging.INFO, "tenancy_ownership_transferred",
            workspace_id=str(workspace_id), from_user_id=str(from_user_id), to_user_id=str(to_user_id),
        )
        await self._audit.record(
            actor_user_id=from_user_id, workspace_id=workspace_id, event_type="tenancy_ownership_transferred",
            metadata={"to_user_id": str(to_user_id)},
        )
        return updated_target

    async def deactivate_workspace(self, *, workspace_id: UUID, acting_role: Role, acting_user_id: UUID) -> Workspace:
        """Only an owner may deactivate a workspace. Memberships are left
        untouched -- ``get_context`` already refuses everyone once the
        workspace itself is inactive, which is the only gate that matters.
        """

        if acting_role is not Role.OWNER:
            raise OwnerRequiredError("Only an owner may deactivate the workspace.")
        workspace = await self._workspaces.update(workspace_id, changes={"is_active": False})
        if workspace is None:
            raise WorkspaceNotFoundError(str(workspace_id))
        log_event(_logger, logging.INFO, "tenancy_workspace_deactivated", workspace_id=str(workspace_id))
        await self._audit.record(
            actor_user_id=acting_user_id, workspace_id=workspace_id, event_type="tenancy_workspace_deactivated",
        )
        return workspace

    # -- audit log -------------------------------------------------------------

    async def list_audit_log(self, *, workspace_id: UUID, limit: int = 50, offset: int = 0) -> list[AuditLogEntry]:
        return await self._audit.list_for_workspace(workspace_id=workspace_id, limit=limit, offset=offset)

    # -- shared plumbing --------------------------------------------------

    async def _require_active_workspace(self, workspace_id: UUID) -> Workspace:
        workspace = await self._workspaces.get(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(str(workspace_id))
        if not workspace.is_active:
            raise WorkspaceInactiveError(str(workspace_id))
        return workspace

    def _compose_invite_message(self, *, workspace: Workspace, email: str, raw_token: str) -> EmailMessage:
        link = f"{self._app_base_url}/invitations/accept?token={raw_token}"
        return EmailMessage(
            to=email, subject=f"You're invited to join {workspace.name}",
            body=(
                f"You've been invited to join the \"{workspace.name}\" workspace.\n\n"
                f"{link}\n\n"
                "If you weren't expecting this, you can safely ignore this email."
            ),
        )
