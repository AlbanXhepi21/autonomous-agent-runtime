"""The centralized role-to-permission mapping."""

import pytest

from app.tenancy.contracts import Role
from app.tenancy.permissions import ROLE_PERMISSIONS, Permission, permissions_for_role


def test_every_role_has_a_mapping() -> None:
    for role in Role:
        assert role in ROLE_PERMISSIONS


def test_owner_has_every_permission() -> None:
    assert permissions_for_role(Role.OWNER) == frozenset(Permission)


def test_permission_sets_are_monotonic_by_seniority() -> None:
    """Everything a viewer can do, an analyst can too; everything an analyst
    can do, an admin can too; everything an admin can do, an owner can too.
    """

    viewer = permissions_for_role(Role.VIEWER)
    analyst = permissions_for_role(Role.ANALYST)
    admin = permissions_for_role(Role.ADMIN)
    owner = permissions_for_role(Role.OWNER)

    assert viewer <= analyst <= admin <= owner


@pytest.mark.parametrize(
    ("role", "permission", "expected"),
    [
        (Role.OWNER, Permission.READ_TENANT_RESOURCES, True),
        (Role.OWNER, Permission.RUN_ANALYSES, True),
        (Role.OWNER, Permission.PUBLISH_REPORTS, True),
        (Role.OWNER, Permission.MANAGE_DATA_SOURCES, True),
        (Role.OWNER, Permission.MANAGE_MEMBERS, True),
        (Role.OWNER, Permission.UPDATE_TENANT_SETTINGS, True),
        (Role.OWNER, Permission.TRANSFER_OWNERSHIP, True),
        (Role.OWNER, Permission.DEACTIVATE_TENANT, True),
        (Role.ADMIN, Permission.READ_TENANT_RESOURCES, True),
        (Role.ADMIN, Permission.RUN_ANALYSES, True),
        (Role.ADMIN, Permission.PUBLISH_REPORTS, True),
        (Role.ADMIN, Permission.MANAGE_DATA_SOURCES, True),
        (Role.ADMIN, Permission.MANAGE_MEMBERS, True),
        (Role.ADMIN, Permission.UPDATE_TENANT_SETTINGS, True),
        (Role.ADMIN, Permission.TRANSFER_OWNERSHIP, False),
        (Role.ADMIN, Permission.DEACTIVATE_TENANT, False),
        (Role.ANALYST, Permission.READ_TENANT_RESOURCES, True),
        (Role.ANALYST, Permission.RUN_ANALYSES, True),
        (Role.ANALYST, Permission.PUBLISH_REPORTS, True),
        (Role.ANALYST, Permission.MANAGE_DATA_SOURCES, False),
        (Role.ANALYST, Permission.MANAGE_MEMBERS, False),
        (Role.ANALYST, Permission.UPDATE_TENANT_SETTINGS, False),
        (Role.ANALYST, Permission.TRANSFER_OWNERSHIP, False),
        (Role.ANALYST, Permission.DEACTIVATE_TENANT, False),
        (Role.VIEWER, Permission.READ_TENANT_RESOURCES, True),
        (Role.VIEWER, Permission.RUN_ANALYSES, False),
        (Role.VIEWER, Permission.PUBLISH_REPORTS, False),
        (Role.VIEWER, Permission.MANAGE_DATA_SOURCES, False),
        (Role.VIEWER, Permission.MANAGE_MEMBERS, False),
        (Role.VIEWER, Permission.UPDATE_TENANT_SETTINGS, False),
        (Role.VIEWER, Permission.TRANSFER_OWNERSHIP, False),
        (Role.VIEWER, Permission.DEACTIVATE_TENANT, False),
    ],
)
def test_role_permission_matrix(role: Role, permission: Permission, expected: bool) -> None:
    assert (permission in permissions_for_role(role)) is expected
