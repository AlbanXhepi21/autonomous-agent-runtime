---
name: change-api
description: Change an autonomous-agent FastAPI route, request or response contract, Pydantic API model, OpenAPI schema, generated TypeScript API type, frontend API call, or SSE event contract. Use for API-boundary work; do not use for styling-only frontend work, internal behavior with no public contract change, or an architecture explanation.
---

# Change API

## Workflow

Follow this order:

```text
Inspect contract and consumers
→ change backend contract/route
→ test backend behavior
→ regenerate OpenAPI snapshot
→ regenerate TypeScript types/client
→ update frontend consumers
→ run type checking and targeted tests
→ inspect schema drift
```

1. Inspect the route, Pydantic schema, service boundary, direct frontend API wrapper, consumers, and closest API tests before editing.
2. Define compatibility: preserve existing fields, error behavior, and event names/shapes unless the request explicitly authorizes a breaking change.
3. Change the smallest backend contract and route. Keep request models `extra="forbid"`; use existing error-envelope conventions; retain authentication, CSRF, permission, and tenant checks.
4. Add or update the backend API test, then run it.
5. Run `cd frontend && npm run gen:api`. This regenerates `frontend/openapi.json` and `frontend/src/types/api.generated.ts`; never hand-edit either output or duplicate generated TypeScript types.
6. Update the hand-written frontend API wrapper and affected consumers. Run their targeted tests and `cd frontend && npm run typecheck`.
7. Inspect the generated diff for unintended schema drift. Update the relevant `docs/api/` page when the HTTP contract materially changes.

## Required checks

- Read [API synchronization](references/api-synchronization.md) before generating or reviewing API outputs.
- Read [repository boundaries](references/repository-boundaries.md) for package ownership and contract tests.
- Read [tenant isolation](references/tenant-isolation.md) for workspace-scoped routes, artifacts, or permissions.
- Read [testing map](references/testing-map.md) when selecting frontend or backend validation.

## Stop and ask

- Authentication, authorization, tenant scope, or backward-compatibility semantics are undefined.
- A proposed API change requires an unapproved breaking migration, destructive action, or unavailable credentials/service.
- Generated schema drift includes unrelated changes, or required consumers cannot be identified.

## Completion report

State: changed route/contracts/events; compatibility decision; generated OpenAPI/types; backend and frontend checks; documentation updated; skipped checks, risks, or blockers.
