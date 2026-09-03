"""The one authoritative shape a tenant-scoped request resolves to.

``app.tenancy.service.TenancyService.get_context`` is the only place that
builds one of these; every tenant-scoped route depends on it (via
``app.api.dependencies.get_tenant_context``) rather than re-deriving
membership or permissions itself.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.identity.contracts import User
from app.tenancy.contracts import Membership, Role, Workspace
from app.tenancy.permissions import Permission


class TenantContext(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    user: User
    workspace: Workspace
    membership: Membership
    role: Role
    permissions: frozenset[Permission]

    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions
