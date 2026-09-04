# Tenant isolation

Load this only for workspace-owned resources, authorization, sessions, permissions, artifacts, or cross-tenant behavior.

- Workspace routes resolve `TenantContext`; use the established permission dependency rather than reconstructing membership checks.
- Scope store reads and writes by `workspace_id` as defense in depth. Cross-tenant access must remain indistinguishable from a missing resource where the existing API follows that convention.
- Preserve CSRF protection on state-changing authenticated routes unless a documented exception applies.
- Test route behavior in `backend/tests/api/test_tenant_isolation.py`; test store behavior with the database-backed isolation tests when configured.

For the exceptions and exact authorization chain, read [authentication and tenancy](../../../../docs/architecture/authentication-and-tenancy.md).
