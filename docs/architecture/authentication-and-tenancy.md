# Authentication and tenancy

This document covers `backend/app/identity/`, `backend/app/tenancy/`, and the per-request
dependency chain in `backend/app/api/dependencies.py` — the currently implemented
behavior only. See [security-boundaries.md](security-boundaries.md) for how this
authorization boundary relates to the other trust boundaries in the system.

## Authentication lifecycle

`AuthService` (`backend/app/identity/service.py`) implements every step:

- **Register** (`POST /api/v1/auth/register`) — normalizes the email, enforces a minimum
  password length, rejects a duplicate email, hashes the password with Argon2id, creates
  the user, and sends an email-verification token. **Registering does not log the user
  in** — no session cookie is set here; only `login` does that.
- **Email verification** — a token emailed at registration (or resent on demand) is
  redeemed once to mark the account verified.
- **Login** (`POST /api/v1/auth/login`) — looks up the user by email; if no account
  exists, the password check still runs against a fixed dummy hash so that a nonexistent
  account and a wrong password take the same amount of time to reject. On success it
  checks the account is active, opportunistically re-hashes the password if the hashing
  parameters have since changed, and creates a session.
- **Logout / logout-all** — revoke one session, or every session for the user (used after
  a password change, see below).
- **Forgot / reset password** — `forgot_password` behaves identically whether or not the
  email is registered (no observable difference in response), so the endpoint can't be
  used to enumerate accounts. `reset_password` redeems a token and revokes **every**
  session for that user.
- **Change password** (authenticated) — re-verifies the current password, then revokes
  every other session except the one making the request.

## Session and token behavior

A session token is 256 bits of `secrets.token_urlsafe` output. Only its SHA-256 hash is
ever stored — the raw token exists solely in the cookie issued to the browser (see
[persistence.md](persistence.md#sessions)). No per-token salt or slow key-derivation is
applied to that hash, deliberately: a token with this much entropy doesn't need one, and
adding one would only make read-heavy session validation slower for no security benefit.

On every request, `get_current_session()` (`backend/app/api/dependencies.py`) reads the
session cookie, hashes it, and looks it up. A session is rejected — uniformly, so the
caller can't distinguish which case applies — if it's not found or already revoked, if it's
past its **absolute** TTL (default 30 days) regardless of activity, or if it's been idle
longer than the **sliding idle** TTL (default 12 hours). A valid lookup "touches" the
session, sliding the idle clock forward. `get_current_user()` layers on top of this and
re-checks the account is still active.

## Cookie security

Two cookies are set together, only from `backend/app/api/routes/auth.py`:

| Cookie | `HttpOnly` | `Secure` | `SameSite` |
|---|---|---|---|
| `session_token` | Yes — never readable from JavaScript | `effective_cookie_secure` | `Lax` |
| `csrf_token` | **No** — deliberately readable, so the frontend can copy it into a header | same | `Lax` |

`effective_cookie_secure` forces `Secure=true` whenever `SECURITY_ENVIRONMENT` is the
literal string `production`, regardless of the `AUTH_COOKIE_SECURE` setting. **This is a
real, easy-to-hit gap**: the other three valid values of that setting — `unknown`
(the default), `development`, and `staging` — do **not** force it. A deployment that
never explicitly sets `SECURITY_ENVIRONMENT=production` will silently run without
`Secure` cookies unless `AUTH_COOKIE_SECURE` is also set by hand.

## CSRF behavior

`require_csrf()` implements a server-verified double-submit pattern, stronger than a bare
cookie-echo check: the request's `X-CSRF-Token` header must hash to the **exact
`csrf_token_hash` stored on that specific session** at login time (compared with
`hmac.compare_digest`), not merely match whatever `csrf_token` cookie happens to be
present. This dependency is attached to essentially every mutating (`POST`/`PATCH`/
`DELETE`) route across the API. `register` and `login` are exempt, since no session exists
yet to check against.

**One inconsistency found**: `POST /api/v1/invitations/accept`
(`backend/app/api/routes/workspaces.py`) is a state-mutating, authenticated endpoint that
does **not** carry `require_csrf`, unlike every other mutating route in the same file. No
comment in the code explains this as an intentional exemption.

## Tenant / workspace model

A `Workspace` is the tenancy root (see [persistence.md](persistence.md)). A `Membership`
links a user to a workspace with one of four roles:

| Role | Permissions |
|---|---|
| `OWNER` | Everything, including transferring ownership and deactivating the workspace |
| `ADMIN` | Read, run analyses, publish reports, manage data sources (create/edit/test/replace credentials/enable/disable), manage members, update workspace settings — **not** ownership transfer, deactivation, or deleting a data source |
| `ANALYST` | Read, run analyses, publish reports |
| `VIEWER` | Read only |

## Permission resolution and tenant-context enforcement

`require_permission(Permission.X)` depends on `get_tenant_context`, which calls
`TenancyService.get_context()` — the single authoritative resolver for "is this user
allowed in this workspace, and with what role." It looks up the workspace (rejecting an
unknown or inactive one), then the caller's membership in it (rejecting a missing or
disabled membership), and only then builds a `TenantContext` carrying that role's
permission set. Every route nested under `/api/v1/workspaces/{workspace_id}/...` depends
on this resolver, with two documented exceptions:

- `backend/app/api/routes/schema.py` — the schema-explorer routes over the process-wide
  demo analytics database intentionally require only a signed-in user, with no workspace
  scoping at all, because that database predates tenancy and has no workspace owner (see
  [`../TENANCY.md`](../TENANCY.md)).
- `backend/app/api/routes/artifacts.py` — its URL shape (`/artifacts/{id}`) carries no
  `workspace_id` path segment for the standard dependency to bind to, so it performs its
  own equivalent check manually.

Enforcement does not stop at the dependency layer. Store methods themselves filter by
`workspace_id` in their queries (for example, membership and workspace lookups both
include `workspace_id` in their `WHERE` clause) — so even a caller that somehow reached a
store call with the wrong workspace ID gets an empty result, not another tenant's row.
This is defense in depth: the dependency layer is the primary gate, and the storage layer
independently refuses to leak across the boundary even if it were bypassed.

## Invitation lifecycle

An owner invites a workspace member by email and role (only an owner may invite another
owner); a duplicate pending invitation to the same email is rejected. The raw invitation
token is generated once, only its hash is stored, and it expires after a configurable TTL
(default 7 days). Accepting an invitation requires the accepting account's email to match
the invitation's email exactly — holding the link alone is not sufficient if you're signed
in as someone else — and creates a membership with the role chosen at invite time, then
marks the invitation single-use. A `mark_revoked` capability exists at the store layer;
this review did not confirm it is currently exposed through the API.

## Cross-tenant isolation

Isolation is verified at two independent layers, both by test:

- **HTTP layer** (`backend/tests/api/test_tenant_isolation.py`) — two synthetic tenants
  share the same backing store, and a real route is called with one tenant's identifier
  while authenticated as the other; every case must return "not found," never a
  distinguishable "forbidden." One test drives this through two genuinely separate
  cookie-authenticated sessions with no dependency override at all, specifically to guard
  against a route regression that drops its `workspace_id` path segment.
- **Repository layer** (`backend/tests/integration/test_tenant_isolation.py`, requires a
  real database) — the same "substitute another tenant's ID" technique applied directly
  against store methods, asserting a row belonging to a different workspace is
  indistinguishable from a row that doesn't exist.

## Known limitations

- `POST /api/v1/invitations/accept` lacks CSRF protection, inconsistent with every other
  mutating route.
- `SECURITY_ENVIRONMENT` only forces `Secure` cookies for the literal value `production`;
  `staging` and the default `unknown` do not, which is easy to leave misconfigured in a
  real deployment.
- The schema-explorer routes over the demo analytics database are intentionally
  unscoped by workspace — a known, separately tracked limitation, not an oversight (see
  [`../TENANCY.md`](../TENANCY.md)).
