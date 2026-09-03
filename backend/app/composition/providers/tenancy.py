"""Workspaces, memberships, invitations, and report preferences."""

from app.composition.lifecycle import provider
from app.composition.providers.audit import get_audit_log_store
from app.composition.providers.identity import get_email_sender
from app.composition.providers.persistence import get_runtime_database
from app.composition.providers.settings import get_settings
from app.tenancy.service import TenancyService
from app.tenancy.store import (
    InMemoryInvitationStore,
    InMemoryMembershipStore,
    InMemoryReportPreferencesStore,
    InMemoryWorkspaceStore,
    InvitationStore,
    MembershipStore,
    ReportPreferencesStore,
    WorkspaceStore,
)


@provider
def get_workspace_store() -> WorkspaceStore:
    settings = get_settings()
    if settings.tenancy_backend == "in_memory":
        return InMemoryWorkspaceStore()
    from app.tenancy.store import PostgresWorkspaceStore

    return PostgresWorkspaceStore(get_runtime_database())


@provider
def get_membership_store() -> MembershipStore:
    settings = get_settings()
    if settings.tenancy_backend == "in_memory":
        return InMemoryMembershipStore()
    from app.tenancy.store import PostgresMembershipStore

    return PostgresMembershipStore(get_runtime_database())


@provider
def get_invitation_store() -> InvitationStore:
    settings = get_settings()
    if settings.tenancy_backend == "in_memory":
        return InMemoryInvitationStore()
    from app.tenancy.store import PostgresInvitationStore

    return PostgresInvitationStore(get_runtime_database())


@provider
def get_report_preferences_store() -> ReportPreferencesStore:
    settings = get_settings()
    if settings.tenancy_backend == "in_memory":
        return InMemoryReportPreferencesStore()
    from app.tenancy.store import PostgresReportPreferencesStore

    return PostgresReportPreferencesStore(get_runtime_database())


@provider
def get_tenancy_service() -> TenancyService:
    settings = get_settings()
    return TenancyService(
        workspaces=get_workspace_store(), memberships=get_membership_store(), invitations=get_invitation_store(),
        email_sender=get_email_sender(), invitation_ttl_seconds=settings.invitation_ttl_seconds,
        app_base_url=settings.app_base_url, report_preferences=get_report_preferences_store(),
        audit=get_audit_log_store(),
    )
