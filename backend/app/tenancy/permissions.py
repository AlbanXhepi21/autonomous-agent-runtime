"""Centralized role-to-permission mapping.

The one place a workspace role is translated into what it may actually do.
API routes depend on ``require_permission(Permission.X)``
(``app.api.dependencies``) and never compare a role name directly -- adding
or narrowing a permission means editing ``ROLE_PERMISSIONS`` here, not
hunting through route handlers.

Deliberately a different vocabulary from ``app.security.permissions``
(``Capability``), which governs what an agent *tool call* may do at
runtime. This module governs what an authenticated HTTP caller may do to
workspace resources -- a different question with a different enum, on
purpose.
"""

from __future__ import annotations

from enum import StrEnum

from app.tenancy.contracts import Role


class Permission(StrEnum):
    READ_TENANT_RESOURCES = "read_tenant_resources"
    RUN_ANALYSES = "run_analyses"
    PUBLISH_REPORTS = "publish_reports"
    MANAGE_DATA_SOURCES = "manage_data_sources"
    #: Deleting a data source connection (even soft-deleted) is more
    #: destructive than editing, testing, or disabling one -- reversing it
    #: means re-onboarding from scratch, the same asymmetry that already
    #: separates TRANSFER_OWNERSHIP/DEACTIVATE_TENANT from
    #: UPDATE_TENANT_SETTINGS. Granted to OWNER only; see ROLE_PERMISSIONS.
    DELETE_DATA_SOURCES = "delete_data_sources"
    MANAGE_MEMBERS = "manage_members"
    UPDATE_TENANT_SETTINGS = "update_tenant_settings"
    TRANSFER_OWNERSHIP = "transfer_ownership"
    DEACTIVATE_TENANT = "deactivate_tenant"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.OWNER: frozenset(Permission),
    Role.ADMIN: frozenset({
        Permission.READ_TENANT_RESOURCES,
        Permission.RUN_ANALYSES,
        Permission.PUBLISH_REPORTS,
        Permission.MANAGE_DATA_SOURCES,
        Permission.MANAGE_MEMBERS,
        Permission.UPDATE_TENANT_SETTINGS,
        # Not TRANSFER_OWNERSHIP, DEACTIVATE_TENANT, or DELETE_DATA_SOURCES --
        # see app.tenancy.service for the matching "admins cannot manage
        # owners" and "only an owner can transfer ownership" rules.
    }),
    Role.ANALYST: frozenset({
        Permission.READ_TENANT_RESOURCES,
        Permission.RUN_ANALYSES,
        Permission.PUBLISH_REPORTS,
    }),
    Role.VIEWER: frozenset({
        Permission.READ_TENANT_RESOURCES,
    }),
}


def permissions_for_role(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]
