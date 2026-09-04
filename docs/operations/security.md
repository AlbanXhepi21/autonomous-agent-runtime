# Operating this system securely

This is operational guidance layered on top of
[security-boundaries.md](../architecture/security-boundaries.md) and
[authentication-and-tenancy.md](../architecture/authentication-and-tenancy.md) — read
those for the mechanisms; this page is what to actually configure and watch for when
running the system.

## The most important setting: `SECURITY_ENVIRONMENT`

Read [limitations.md](../reference/limitations.md#the-production-security-environment-is-a-near-total-kill-switch-not-a-tightening)
before setting this to `production`. It denies almost every read-only and analytics tool
outright — this is not a mild tightening, and treating it as one will produce a
non-functional deployment, not a merely-stricter one. Whatever value you choose, set it
**explicitly** rather than leaving the default `unknown` — the default does not force
`Secure` cookies, and only the literal string `production` does.

## Tenant isolation

Enforced at two independent layers: the per-route `TenantContext` dependency, and
`workspace_id` filtering inside the store queries themselves (see
[authentication-and-tenancy.md](../architecture/authentication-and-tenancy.md#permission-resolution-and-tenant-context-enforcement)).
Two routes are documented, deliberate exceptions to workspace scoping — the schema
explorer (over the process-wide demo database) and the artifacts download route (which
does its own manual check because its URL carries no workspace segment). Both are
known and intentional, not oversights — see [`../TENANCY.md`](../TENANCY.md).

## Authentication security

- Passwords are hashed with Argon2id, with opportunistic rehashing on login if parameters
  change.
- Sessions are server-side, cookie-referenced, never JWTs; only hashed tokens are ever
  stored.
- **Known gap**: `POST /api/v1/invitations/accept` currently lacks CSRF protection,
  inconsistent with every other mutating route — see
  [authentication-and-tenancy.md](../architecture/authentication-and-tenancy.md#csrf-behavior).
  Treat invitation acceptance as a higher-scrutiny code path until this is closed.
- No MFA, no OAuth/SSO exists — if your deployment needs either, it is not currently
  available and would need to be built.

## Credential handling

Secrets referenced by this application (`OPENAI_API_KEY`, `DATABASE_URL`, `GITHUB_TOKEN`,
`SMTP_PASSWORD`, `DATA_SOURCE_ENCRYPTION_KEY`) are resolved through a logical-reference
indirection (`SecretReference`/`CredentialProvider`), never passed around as raw strings
by name. Two of them — `SMTP_PASSWORD` and `GITHUB_TOKEN` — are read directly from the
**process environment**, not from `backend/.env`'s pydantic-settings loader; putting them
only in `.env` will not work in any environment, local or production. See
[configuration.md](../getting-started/configuration.md#two-variables-that-bypass-env-entirely).

Rotate `DATA_SOURCE_ENCRYPTION_KEY` deliberately and rarely: rotating it invalidates every
already-stored workspace data-source password, requiring each to be re-entered.

## Prompt-injection posture

Trust boundaries around tool output are enforced structurally where they exist (e.g.
`read_file`/repository-tool output is tagged `UNTRUSTED_EXTERNAL`), but the
injection-pattern detection layered on top is explicitly heuristic and diagnostic —
it labels, it does not block. The project's own stated position (echoed in
`README.md`) is that injection resistance has not been benchmarked end-to-end. Do not
represent this system as hardened against prompt injection in any external-facing
security documentation.

## Sandbox guarantees, precisely

The restricted Python (`python_exec`, `analyze_dataset`) and command execution
(`run_command`) sandboxes are process-isolation and import/allowlist filtering, explicitly
**not** a hardened, hostile-code-safe sandbox — this is stated in the code's own
docstrings, not just inferred. Both require human approval before executing at all (see
[agent-runtime.md](../architecture/agent-runtime.md#human-approval-checkpoints)), which is
the primary control, not sandbox strength alone. Do not run this system's agent with
approval gating disabled against untrusted input.

## What to monitor operationally

Since there's no external observability integration (see
[observability.md](observability.md)), watch, at minimum, via your own log aggregation:
approval-request creation and resolution (a growing backlog means a human isn't
responding), authentication failure rate (login/register rate limiting exists per-IP but
nothing alerts on it), and the two worker scripts' own exit status if you run them under a
supervisor that logs restarts.
