"""Persistence for workspaces, memberships, and invitations.

Follows the same shape as ``app.identity.store``: an abstract contract
naming the operations, an in-process implementation for tests and
zero-config development, and one PostgreSQL implementation for a real
deployment, selected the same way ``IDENTITY_BACKEND`` already selects
between its own two implementations.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from app.db.records import (
    ReportPreferencesRecord,
    WorkspaceInvitationRecord,
    WorkspaceMembershipRecord,
    WorkspaceRecord,
)
from app.db.session import Database
from app.tenancy.contracts import Invitation, Membership, MembershipStatus, ReportPreferences, Role, Workspace


def _now() -> datetime:
    return datetime.now(UTC)


class WorkspaceVersionConflictError(Exception):
    """Raised when an update's expected version does not match the stored one."""

    def __init__(self, *, expected: int, actual: int) -> None:
        super().__init__(f"Expected version {expected}, but the stored version is {actual}.")
        self.expected = expected
        self.actual = actual


class ReportPreferencesVersionConflictError(Exception):
    """Raised when an update's expected version does not match the stored one."""

    def __init__(self, *, expected: int, actual: int) -> None:
        super().__init__(f"Expected version {expected}, but the stored version is {actual}.")
        self.expected = expected
        self.actual = actual


# -- workspace store ------------------------------------------------------


class WorkspaceStore(ABC):
    @abstractmethod
    async def create(
        self, *, name: str, slug: str, logo_ref: str | None,
        default_timezone: str, default_locale: str, default_currency: str,
    ) -> Workspace: ...

    @abstractmethod
    async def get(self, workspace_id: UUID) -> Workspace | None: ...

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Workspace | None:
        """``slug`` must already be normalized -- this performs an exact match."""

    @abstractmethod
    async def update(
        self, workspace_id: UUID, *, changes: dict[str, Any], expected_version: int | None = None,
    ) -> Workspace | None:
        """Apply a partial update (settings edits, or ``is_active=False`` to deactivate).

        ``expected_version`` is optional: internal single-field mutations
        (deactivation, ownership bookkeeping) skip the check, since there is
        no realistic concurrent-edit race for them. A caller-driven settings
        edit always supplies it -- see ``TenancyService.update_settings``.
        Every successful update bumps the stored version by one, whether or
        not the caller checked it.
        """


def _workspace_to_domain(record: WorkspaceRecord) -> Workspace:
    return Workspace(
        id=record.id, name=record.name, slug=record.slug, logo_ref=record.logo_ref,
        is_active=record.is_active, default_timezone=record.default_timezone,
        default_locale=record.default_locale, default_currency=record.default_currency,
        fiscal_year_start_month=record.fiscal_year_start_month, number_format=record.number_format,
        date_format=record.date_format, version=record.version,
        created_at=record.created_at, updated_at=record.updated_at,
    )


class InMemoryWorkspaceStore(WorkspaceStore):
    def __init__(self) -> None:
        self._workspaces: dict[UUID, Workspace] = {}
        self._lock = asyncio.Lock()

    async def create(
        self, *, name: str, slug: str, logo_ref: str | None,
        default_timezone: str, default_locale: str, default_currency: str,
    ) -> Workspace:
        async with self._lock:
            if any(existing.slug == slug for existing in self._workspaces.values()):
                raise ValueError(f"Slug already exists: {slug}")
            now = _now()
            workspace = Workspace(
                id=uuid4(), name=name, slug=slug, logo_ref=logo_ref, is_active=True,
                default_timezone=default_timezone, default_locale=default_locale,
                default_currency=default_currency, created_at=now, updated_at=now,
            )
            self._workspaces[workspace.id] = workspace
            return workspace

    async def get(self, workspace_id: UUID) -> Workspace | None:
        async with self._lock:
            return self._workspaces.get(workspace_id)

    async def get_by_slug(self, slug: str) -> Workspace | None:
        async with self._lock:
            return next((item for item in self._workspaces.values() if item.slug == slug), None)

    async def update(
        self, workspace_id: UUID, *, changes: dict[str, Any], expected_version: int | None = None,
    ) -> Workspace | None:
        async with self._lock:
            existing = self._workspaces.get(workspace_id)
            if existing is None:
                return None
            if expected_version is not None and existing.version != expected_version:
                raise WorkspaceVersionConflictError(expected=expected_version, actual=existing.version)
            updated = existing.model_copy(update={**changes, "version": existing.version + 1, "updated_at": _now()})
            self._workspaces[workspace_id] = updated
            return updated


class PostgresWorkspaceStore(WorkspaceStore):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def close(self) -> None:
        """Release the connection pool this store owns, at application shutdown."""

        await self._database.dispose()

    async def create(
        self, *, name: str, slug: str, logo_ref: str | None,
        default_timezone: str, default_locale: str, default_currency: str,
    ) -> Workspace:
        now = _now()
        record = WorkspaceRecord(
            id=uuid4(), name=name, slug=slug, logo_ref=logo_ref, is_active=True,
            default_timezone=default_timezone, default_locale=default_locale,
            default_currency=default_currency, created_at=now, updated_at=now,
        )
        async with self._database.session() as session, session.begin():
            session.add(record)
        return _workspace_to_domain(record)

    async def get(self, workspace_id: UUID) -> Workspace | None:
        async with self._database.session() as session:
            record = await session.get(WorkspaceRecord, workspace_id)
        return _workspace_to_domain(record) if record is not None else None

    async def get_by_slug(self, slug: str) -> Workspace | None:
        async with self._database.session() as session:
            record = await session.scalar(select(WorkspaceRecord).where(WorkspaceRecord.slug == slug))
        return _workspace_to_domain(record) if record is not None else None

    async def update(
        self, workspace_id: UUID, *, changes: dict[str, Any], expected_version: int | None = None,
    ) -> Workspace | None:
        async with self._database.session() as session, session.begin():
            record = await session.get(WorkspaceRecord, workspace_id)
            if record is None:
                return None
            if expected_version is not None and record.version != expected_version:
                raise WorkspaceVersionConflictError(expected=expected_version, actual=record.version)
            for field, value in changes.items():
                setattr(record, field, value)
            record.version += 1
            record.updated_at = _now()
        return _workspace_to_domain(record)


# -- report preferences store ----------------------------------------------


class ReportPreferencesStore(ABC):
    """One row per workspace, created lazily on first read -- there is
    nothing to migrate a pre-existing workspace into, unlike ``memberships``.
    """

    @abstractmethod
    async def get_or_create(self, *, workspace_id: UUID) -> ReportPreferences:
        """Return the workspace's preferences, creating an all-defaults row if none exists yet."""

    @abstractmethod
    async def update(
        self, *, workspace_id: UUID, expected_version: int, changes: dict[str, Any],
    ) -> ReportPreferences:
        """Raises ``ReportPreferencesVersionConflictError`` on a stale ``expected_version``."""


def _report_preferences_to_domain(record: ReportPreferencesRecord) -> ReportPreferences:
    return ReportPreferences(
        workspace_id=record.workspace_id, default_template=record.default_template,
        default_output_format=record.default_output_format, default_theme=record.default_theme,
        default_narrative_policy=record.default_narrative_policy,
        evidence_appendix_enabled=record.evidence_appendix_enabled,
        technical_sql_appendix_enabled=record.technical_sql_appendix_enabled,
        version=record.version, created_at=record.created_at, updated_at=record.updated_at,
    )


class InMemoryReportPreferencesStore(ReportPreferencesStore):
    def __init__(self) -> None:
        self._preferences: dict[UUID, ReportPreferences] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, *, workspace_id: UUID) -> ReportPreferences:
        async with self._lock:
            existing = self._preferences.get(workspace_id)
            if existing is not None:
                return existing
            now = _now()
            created = ReportPreferences(workspace_id=workspace_id, created_at=now, updated_at=now)
            self._preferences[workspace_id] = created
            return created

    async def update(
        self, *, workspace_id: UUID, expected_version: int, changes: dict[str, Any],
    ) -> ReportPreferences:
        async with self._lock:
            existing = self._preferences.get(workspace_id)
            if existing is None:
                existing = ReportPreferences(workspace_id=workspace_id, created_at=_now(), updated_at=_now())
            if existing.version != expected_version:
                raise ReportPreferencesVersionConflictError(expected=expected_version, actual=existing.version)
            updated = existing.model_copy(update={**changes, "version": existing.version + 1, "updated_at": _now()})
            self._preferences[workspace_id] = updated
            return updated


class PostgresReportPreferencesStore(ReportPreferencesStore):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def close(self) -> None:
        await self._database.dispose()

    async def get_or_create(self, *, workspace_id: UUID) -> ReportPreferences:
        async with self._database.session() as session:
            record = await session.get(ReportPreferencesRecord, workspace_id)
        if record is not None:
            return _report_preferences_to_domain(record)
        now = _now()
        record = ReportPreferencesRecord(workspace_id=workspace_id, created_at=now, updated_at=now)
        async with self._database.session() as session, session.begin():
            # Another request may have created the row between the read above
            # and this write; a unique-violation there is just as valid a
            # "someone else already created it" signal as the record existing.
            existing = await session.get(ReportPreferencesRecord, workspace_id)
            if existing is not None:
                return _report_preferences_to_domain(existing)
            session.add(record)
        return _report_preferences_to_domain(record)

    async def update(
        self, *, workspace_id: UUID, expected_version: int, changes: dict[str, Any],
    ) -> ReportPreferences:
        async with self._database.session() as session, session.begin():
            record = await session.get(ReportPreferencesRecord, workspace_id)
            if record is None:
                now = _now()
                record = ReportPreferencesRecord(workspace_id=workspace_id, created_at=now, updated_at=now)
                session.add(record)
                await session.flush()
            if record.version != expected_version:
                raise ReportPreferencesVersionConflictError(expected=expected_version, actual=record.version)
            for field, value in changes.items():
                setattr(record, field, value)
            record.version += 1
            record.updated_at = _now()
        return _report_preferences_to_domain(record)


# -- membership store -----------------------------------------------------


class MembershipStore(ABC):
    @abstractmethod
    async def create(
        self, *, user_id: UUID, workspace_id: UUID, role: Role, status: MembershipStatus,
        invited_by: UUID | None, joined_at: datetime | None,
    ) -> Membership: ...

    @abstractmethod
    async def get(self, membership_id: UUID) -> Membership | None: ...

    @abstractmethod
    async def get_for_user(self, *, workspace_id: UUID, user_id: UUID) -> Membership | None: ...

    @abstractmethod
    async def list_for_workspace(self, *, workspace_id: UUID, status: MembershipStatus | None = None) -> list[Membership]: ...

    @abstractmethod
    async def list_for_user(self, *, user_id: UUID) -> list[Membership]:
        """Every workspace a user belongs to, any status."""

    @abstractmethod
    async def count_active_owners(self, *, workspace_id: UUID) -> int:
        """How many ACTIVE owner memberships exist -- the last-owner-protection check."""

    @abstractmethod
    async def update_role(self, membership_id: UUID, *, role: Role) -> Membership | None: ...

    @abstractmethod
    async def update_status(self, membership_id: UUID, *, status: MembershipStatus) -> Membership | None: ...


def _membership_to_domain(record: WorkspaceMembershipRecord) -> Membership:
    return Membership(
        id=record.id, user_id=record.user_id, workspace_id=record.workspace_id,
        role=Role(record.role), status=MembershipStatus(record.status),
        invited_by=record.invited_by, joined_at=record.joined_at,
        created_at=record.created_at, updated_at=record.updated_at,
    )


class InMemoryMembershipStore(MembershipStore):
    def __init__(self) -> None:
        self._memberships: dict[UUID, Membership] = {}
        self._lock = asyncio.Lock()

    async def create(
        self, *, user_id: UUID, workspace_id: UUID, role: Role, status: MembershipStatus,
        invited_by: UUID | None, joined_at: datetime | None,
    ) -> Membership:
        async with self._lock:
            if any(
                item.user_id == user_id and item.workspace_id == workspace_id
                for item in self._memberships.values()
            ):
                raise ValueError(f"Membership already exists for user {user_id} in workspace {workspace_id}")
            now = _now()
            membership = Membership(
                id=uuid4(), user_id=user_id, workspace_id=workspace_id, role=role, status=status,
                invited_by=invited_by, joined_at=joined_at, created_at=now, updated_at=now,
            )
            self._memberships[membership.id] = membership
            return membership

    async def get(self, membership_id: UUID) -> Membership | None:
        async with self._lock:
            return self._memberships.get(membership_id)

    async def get_for_user(self, *, workspace_id: UUID, user_id: UUID) -> Membership | None:
        async with self._lock:
            return next(
                (item for item in self._memberships.values()
                 if item.workspace_id == workspace_id and item.user_id == user_id),
                None,
            )

    async def list_for_workspace(self, *, workspace_id: UUID, status: MembershipStatus | None = None) -> list[Membership]:
        async with self._lock:
            return [
                item for item in self._memberships.values()
                if item.workspace_id == workspace_id and (status is None or item.status is status)
            ]

    async def list_for_user(self, *, user_id: UUID) -> list[Membership]:
        async with self._lock:
            return [item for item in self._memberships.values() if item.user_id == user_id]

    async def count_active_owners(self, *, workspace_id: UUID) -> int:
        async with self._lock:
            return sum(
                1 for item in self._memberships.values()
                if item.workspace_id == workspace_id and item.role is Role.OWNER
                and item.status is MembershipStatus.ACTIVE
            )

    async def update_role(self, membership_id: UUID, *, role: Role) -> Membership | None:
        async with self._lock:
            existing = self._memberships.get(membership_id)
            if existing is None:
                return None
            updated = existing.model_copy(update={"role": role, "updated_at": _now()})
            self._memberships[membership_id] = updated
            return updated

    async def update_status(self, membership_id: UUID, *, status: MembershipStatus) -> Membership | None:
        async with self._lock:
            existing = self._memberships.get(membership_id)
            if existing is None:
                return None
            updated = existing.model_copy(update={"status": status, "updated_at": _now()})
            self._memberships[membership_id] = updated
            return updated


class PostgresMembershipStore(MembershipStore):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def close(self) -> None:
        await self._database.dispose()

    async def create(
        self, *, user_id: UUID, workspace_id: UUID, role: Role, status: MembershipStatus,
        invited_by: UUID | None, joined_at: datetime | None,
    ) -> Membership:
        now = _now()
        record = WorkspaceMembershipRecord(
            id=uuid4(), user_id=user_id, workspace_id=workspace_id, role=role.value, status=status.value,
            invited_by=invited_by, joined_at=joined_at, created_at=now, updated_at=now,
        )
        async with self._database.session() as session, session.begin():
            session.add(record)
        return _membership_to_domain(record)

    async def get(self, membership_id: UUID) -> Membership | None:
        async with self._database.session() as session:
            record = await session.get(WorkspaceMembershipRecord, membership_id)
        return _membership_to_domain(record) if record is not None else None

    async def get_for_user(self, *, workspace_id: UUID, user_id: UUID) -> Membership | None:
        async with self._database.session() as session:
            record = await session.scalar(
                select(WorkspaceMembershipRecord).where(
                    WorkspaceMembershipRecord.workspace_id == workspace_id,
                    WorkspaceMembershipRecord.user_id == user_id,
                )
            )
        return _membership_to_domain(record) if record is not None else None

    async def list_for_workspace(self, *, workspace_id: UUID, status: MembershipStatus | None = None) -> list[Membership]:
        async with self._database.session() as session:
            query = select(WorkspaceMembershipRecord).where(WorkspaceMembershipRecord.workspace_id == workspace_id)
            if status is not None:
                query = query.where(WorkspaceMembershipRecord.status == status.value)
            records = (await session.scalars(query.order_by(WorkspaceMembershipRecord.created_at))).all()
        return [_membership_to_domain(record) for record in records]

    async def list_for_user(self, *, user_id: UUID) -> list[Membership]:
        async with self._database.session() as session:
            records = (await session.scalars(
                select(WorkspaceMembershipRecord).where(WorkspaceMembershipRecord.user_id == user_id)
            )).all()
        return [_membership_to_domain(record) for record in records]

    async def count_active_owners(self, *, workspace_id: UUID) -> int:
        async with self._database.session() as session:
            records = (await session.scalars(
                select(WorkspaceMembershipRecord).where(
                    WorkspaceMembershipRecord.workspace_id == workspace_id,
                    WorkspaceMembershipRecord.role == Role.OWNER.value,
                    WorkspaceMembershipRecord.status == MembershipStatus.ACTIVE.value,
                )
            )).all()
        return len(records)

    async def update_role(self, membership_id: UUID, *, role: Role) -> Membership | None:
        async with self._database.session() as session, session.begin():
            record = await session.get(WorkspaceMembershipRecord, membership_id)
            if record is None:
                return None
            record.role = role.value
            record.updated_at = _now()
        return _membership_to_domain(record)

    async def update_status(self, membership_id: UUID, *, status: MembershipStatus) -> Membership | None:
        async with self._database.session() as session, session.begin():
            record = await session.get(WorkspaceMembershipRecord, membership_id)
            if record is None:
                return None
            record.status = status.value
            record.updated_at = _now()
        return _membership_to_domain(record)


# -- invitation store -------------------------------------------------------


class InvitationStore(ABC):
    @abstractmethod
    async def create(
        self, *, workspace_id: UUID, email: str, role: Role, token_hash: str,
        invited_by: UUID | None, expires_at: datetime,
    ) -> Invitation: ...

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> Invitation | None: ...

    @abstractmethod
    async def get_pending(self, *, workspace_id: UUID, email: str) -> Invitation | None:
        """The one outstanding, unexpired, unaccepted invitation for (workspace, email), if any."""

    @abstractmethod
    async def mark_accepted(self, invitation_id: UUID, *, at: datetime) -> None: ...

    @abstractmethod
    async def mark_revoked(self, invitation_id: UUID, *, at: datetime) -> None: ...


def _invitation_to_domain(record: WorkspaceInvitationRecord) -> Invitation:
    return Invitation(
        id=record.id, workspace_id=record.workspace_id, email=record.email, role=Role(record.role),
        token_hash=record.token_hash, invited_by=record.invited_by, created_at=record.created_at,
        expires_at=record.expires_at, accepted_at=record.accepted_at, revoked_at=record.revoked_at,
    )


def _is_pending(invitation: Invitation, *, now: datetime) -> bool:
    return invitation.accepted_at is None and invitation.revoked_at is None and invitation.expires_at >= now


class InMemoryInvitationStore(InvitationStore):
    def __init__(self) -> None:
        self._invitations: dict[UUID, Invitation] = {}
        self._lock = asyncio.Lock()

    async def create(
        self, *, workspace_id: UUID, email: str, role: Role, token_hash: str,
        invited_by: UUID | None, expires_at: datetime,
    ) -> Invitation:
        async with self._lock:
            invitation = Invitation(
                id=uuid4(), workspace_id=workspace_id, email=email, role=role, token_hash=token_hash,
                invited_by=invited_by, created_at=_now(), expires_at=expires_at,
                accepted_at=None, revoked_at=None,
            )
            self._invitations[invitation.id] = invitation
            return invitation

    async def get_by_token_hash(self, token_hash: str) -> Invitation | None:
        async with self._lock:
            return next((item for item in self._invitations.values() if item.token_hash == token_hash), None)

    async def get_pending(self, *, workspace_id: UUID, email: str) -> Invitation | None:
        async with self._lock:
            now = _now()
            return next(
                (
                    item for item in self._invitations.values()
                    if item.workspace_id == workspace_id and item.email == email and _is_pending(item, now=now)
                ),
                None,
            )

    async def mark_accepted(self, invitation_id: UUID, *, at: datetime) -> None:
        async with self._lock:
            existing = self._invitations.get(invitation_id)
            if existing is None:
                return
            self._invitations[invitation_id] = existing.model_copy(update={"accepted_at": at})

    async def mark_revoked(self, invitation_id: UUID, *, at: datetime) -> None:
        async with self._lock:
            existing = self._invitations.get(invitation_id)
            if existing is None:
                return
            self._invitations[invitation_id] = existing.model_copy(update={"revoked_at": at})


class PostgresInvitationStore(InvitationStore):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def close(self) -> None:
        await self._database.dispose()

    async def create(
        self, *, workspace_id: UUID, email: str, role: Role, token_hash: str,
        invited_by: UUID | None, expires_at: datetime,
    ) -> Invitation:
        record = WorkspaceInvitationRecord(
            id=uuid4(), workspace_id=workspace_id, email=email, role=role.value, token_hash=token_hash,
            invited_by=invited_by, created_at=_now(), expires_at=expires_at,
            accepted_at=None, revoked_at=None,
        )
        async with self._database.session() as session, session.begin():
            session.add(record)
        return _invitation_to_domain(record)

    async def get_by_token_hash(self, token_hash: str) -> Invitation | None:
        async with self._database.session() as session:
            record = await session.scalar(
                select(WorkspaceInvitationRecord).where(WorkspaceInvitationRecord.token_hash == token_hash)
            )
        return _invitation_to_domain(record) if record is not None else None

    async def get_pending(self, *, workspace_id: UUID, email: str) -> Invitation | None:
        async with self._database.session() as session:
            record = await session.scalar(
                select(WorkspaceInvitationRecord).where(
                    WorkspaceInvitationRecord.workspace_id == workspace_id,
                    WorkspaceInvitationRecord.email == email,
                    WorkspaceInvitationRecord.accepted_at.is_(None),
                    WorkspaceInvitationRecord.revoked_at.is_(None),
                    WorkspaceInvitationRecord.expires_at >= _now(),
                )
            )
        return _invitation_to_domain(record) if record is not None else None

    async def mark_accepted(self, invitation_id: UUID, *, at: datetime) -> None:
        async with self._database.session() as session, session.begin():
            record = await session.get(WorkspaceInvitationRecord, invitation_id)
            if record is None:
                return
            record.accepted_at = at

    async def mark_revoked(self, invitation_id: UUID, *, at: datetime) -> None:
        async with self._database.session() as session, session.begin():
            record = await session.get(WorkspaceInvitationRecord, invitation_id)
            if record is None:
                return
            record.revoked_at = at
