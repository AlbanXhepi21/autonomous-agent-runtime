# Permissions

This is the tenant role-permission matrix, derived directly from the centralized mapping
in [`backend/app/tenancy/permissions.py`](../../backend/app/tenancy/permissions.py) — the
module's own docstring states it is "the one place a workspace role is translated into
what it may actually do," and that API routes depend on
`require_permission(Permission.X)` rather than ever comparing a role name directly.

## This is a different system from tool `Capability`

`Permission` (this page) governs what an **authenticated HTTP caller** may do to
**workspace resources** — create a report, invite a member, change settings. It is a
completely different vocabulary from `Capability`
(see [tools-skills-and-specialists.md](../concepts/tools-skills-and-specialists.md)),
which governs what an **agent tool call** may do at runtime. The module docstring is
explicit that this separation is deliberate — two different questions, two different
enums, on purpose. Don't conflate a workspace role like `ANALYST` with a tool's risk
level; they don't interact.

## The permission enum

```
READ_TENANT_RESOURCES
RUN_ANALYSES
PUBLISH_REPORTS
MANAGE_DATA_SOURCES
MANAGE_MEMBERS
UPDATE_TENANT_SETTINGS
TRANSFER_OWNERSHIP
DEACTIVATE_TENANT
```

## The role-permission matrix

| Permission | OWNER | ADMIN | ANALYST | VIEWER |
|---|---|---|---|---|
| `READ_TENANT_RESOURCES` | ✅ | ✅ | ✅ | ✅ |
| `RUN_ANALYSES` | ✅ | ✅ | ✅ | — |
| `PUBLISH_REPORTS` | ✅ | ✅ | ✅ | — |
| `MANAGE_DATA_SOURCES` | ✅ | ✅ | — | — |
| `MANAGE_MEMBERS` | ✅ | ✅ | — | — |
| `UPDATE_TENANT_SETTINGS` | ✅ | ✅ | — | — |
| `TRANSFER_OWNERSHIP` | ✅ | — | — | — |
| `DEACTIVATE_TENANT` | ✅ | — | — | — |

`OWNER` holds every permission (`frozenset(Permission)` — the whole enum, not an
enumerated subset, so it can never silently fall out of sync as new permissions are
added). `ADMIN` is deliberately withheld exactly two permissions —
`TRANSFER_OWNERSHIP` and `DEACTIVATE_TENANT` — with a code comment cross-referencing the
matching business rules in `app.tenancy.service`: an admin cannot manage an owner, and
only an owner can transfer ownership.

## How this is enforced

`require_permission(Permission.X)` (`backend/app/api/dependencies.py`) resolves a
`TenantContext` via `TenancyService.get_context()` — the single authoritative resolver
that checks the workspace exists and is active, then that the caller has an active
membership in it — and checks the resulting role's permission set. See
[authentication-and-tenancy.md](../architecture/authentication-and-tenancy.md#permission-resolution-and-tenant-context-enforcement)
for the full resolution chain, the two documented routes that don't go through it, and how
store-level queries independently re-scope by `workspace_id` beneath the dependency layer.
