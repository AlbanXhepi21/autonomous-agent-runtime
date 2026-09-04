# API overview

This is a map of the API, not a reproduction of the OpenAPI schema — for the full,
authoritative, field-by-field contract, generate or read the schema itself (see
[OpenAPI and type generation](#openapi-and-type-generation) below). Every claim here was
checked against `backend/app/main.py` and the route files directly.

## Base path

There is **no single global prefix** applied once — `create_app()`
(`backend/app/main.py`) builds a bare `FastAPI()` and each of the 17 routers declares its
own full prefix independently. 16 of 17 start with `/api/v1`; the one exception is the
artifacts router (`/artifacts`, no version segment) — deliberate, because artifact links
are embedded in already-sent delivery emails/webhooks and must never change shape. See
[reports-and-artifacts.md](reports-and-artifacts.md).

Router prefixes, grouped by resource:

| Group | Prefix |
|---|---|
| Auth | `/api/v1/auth` |
| Users | `/api/v1/users` |
| Workspaces + invitations | `/api/v1/workspaces`, `/api/v1/invitations` |
| Agent (plain goal-driven run) | `/api/v1/workspaces/{workspace_id}/agent` |
| Approvals | `/api/v1/workspaces/{workspace_id}` |
| Traces | `/api/v1/workspaces/{workspace_id}/runs` |
| Analytics (the Workbench's run/report lifecycle) | `/api/v1/workspaces/{workspace_id}/analytics` |
| Conversations | `/api/v1/workspaces/{workspace_id}/conversations` |
| Saved / scheduled reports | `/api/v1/workspaces/{workspace_id}/reports/saved`, `.../reports/scheduled` |
| Deliveries | `/api/v1/workspaces/{workspace_id}/deliveries` |
| Data sources | `/api/v1/workspaces/{workspace_id}/datasources` |
| Schema explorer (process-wide demo DB) | `/api/v1/schema` |
| Memory inspector (developer mode only) | `/api/v1/workspaces/{workspace_id}/memory` |
| Server config | `/api/v1/config` |
| **Artifacts (no `/api/v1`, no workspace prefix)** | `/artifacts` |

## Authentication

Cookie-based server-side sessions, never JWTs — see
[authentication.md](authentication.md) for the full flow. Every workspace-scoped route
requires a valid `session_token` cookie, and every mutating route additionally requires an
`X-CSRF-Token` header matching that session's own CSRF hash.

## Tenant context

Every route nested under `/api/v1/workspaces/{workspace_id}/...` resolves a
`TenantContext` before any domain logic runs — see
[authentication-and-tenancy.md](../architecture/authentication-and-tenancy.md#permission-resolution-and-tenant-context-enforcement)
for the exact resolution chain and the two documented routes that don't go through it
(`schema.py`'s process-wide demo-database routes, and `artifacts.py`'s manual check).

## Error format

Not fully uniform — know this before writing a client that assumes one shape everywhere.
The dominant convention, used across most routes, is a structured envelope:

```json
{"detail": {"code": "unknown_run", "message": "Run not found."}}
```

But a real minority of routes (`artifacts.py`, `traces.py`, `approvals.py`) raise a plain
string instead:

```json
{"detail": "Artifact not found."}
```

**422 validation errors are FastAPI's unmodified default shape** — there is no global
exception handler in this codebase, so a request body that fails Pydantic validation
returns `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`, a different shape
again from both of the above. A robust client should check for `detail` being an object
with `code`/`message`, a plain string, or a validation-error array, rather than assuming
one form.

## Pagination

Real `limit`/`offset` pagination (query params, response includes `items`, `total`,
`limit`, `offset`) exists on: conversations, saved reports, saved-report executions,
scheduled reports, and data sources. The audit log endpoint accepts `limit`/`offset` but
its response omits `total` — weaker pagination. Everything else (artifacts list, report
templates, metrics, run-event history) returns a **full, unpaginated array**. There is no
cursor-based pagination anywhere in this API.

## Important endpoint groups

- **Analytics** (the Workbench's actual workflow — see [analytics.md](analytics.md)):
  create/read a run, stream its events, check report suitability, preview and publish
  reports, list templates and metrics.
- **Reports and artifacts** (see [reports-and-artifacts.md](reports-and-artifacts.md)):
  saved-report CRUD and execution, scheduled-report CRUD, artifact download/list/preview.
- **Auth and tenancy** (see [authentication.md](authentication.md) and
  [`../architecture/authentication-and-tenancy.md`](../architecture/authentication-and-tenancy.md)):
  register/login/logout/password-reset/email-verification, workspace/membership/invitation
  management.
- **Data sources**: workspace-connected PostgreSQL onboarding — see
  [`../DATASOURCES.md`](../DATASOURCES.md).
- **Schema explorer**: read-only introspection of the process-wide demo database, gated
  only by "signed in," not by workspace — a documented, pre-tenancy exception.

## SSE event lifecycle

Covered in full in [streaming-events.md](streaming-events.md). In short: named SSE events,
each carrying a JSON `PublicRunEvent`, streamed while a run executes; the connection closes
automatically once the run reaches a terminal state.

## Report and artifact states

A run's `status` is one of `running`, `completed`, `failed`, `waiting_for_approval`. An
artifact's `status` is one of `PENDING`, `READY`, `FAILED`, `DELETED` — but this value is
**never exposed** in the artifacts API: both the list and get endpoints filter to `READY`
only, so a non-ready artifact is indistinguishable from one that doesn't exist (a plain
404). See [reports-and-artifacts.md](reports-and-artifacts.md).

## OpenAPI and type generation

The live schema is served at `/openapi.json` (FastAPI's unmodified default — no custom
`openapi_url`/`docs_url` is configured; interactive docs are at `/docs`). It can also be
dumped offline, without a running server:

```bash
cd backend && .venv/bin/python -m scripts.dump_openapi
# writes to frontend/openapi.json by default
```

The frontend never hand-writes its API types — regenerate them after any backend API
change:

```bash
cd frontend && npm run gen:api
# runs: cd ../backend && .venv/bin/python -m scripts.dump_openapi
#   && cd ../frontend && openapi-typescript openapi.json -o src/types/api.generated.ts
```

Forgetting this fails `backend/tests/contracts/test_openapi_snapshot.py`, which compares
the live schema against the committed `frontend/openapi.json` (semantically, via
normalized JSON comparison, not byte-for-byte) — see [testing.md](../guides/testing.md#openapi-snapshot).
