# Frontend architecture

The frontend ("the Workbench") is a Next.js 16 App Router application
(`frontend/src/`) with no API routes of its own — every data operation goes to the
FastAPI backend over `NEXT_PUBLIC_API_BASE_URL`. There is no state-management library
(no Redux/Zustand/react-query/SWR); state is plain React hooks and Context, plus a
custom `EventSource`-based hook for streaming run progress.

## Route structure

`frontend/src/app/` is organized around one auth gate:

- **Public routes** (no session required): `/login`, `/register`, `/forgot-password`,
  `/reset-password`, `/verify-email`, `/invitations/accept`, `/confirm-email-change`.
- **`(app)/` route group** — everything behind
  [`(app)/layout.tsx`](<../../frontend/src/app/(app)/layout.tsx>), which calls
  `getServerUser()` server-side and redirects to `/login?expired=1` on an invalid session
  before rendering anything underneath. This is a real session check against the backend
  (`GET /api/v1/auth/me`), not just a cookie-presence check.
  - `(app)/page.tsx` — post-login tenant resolution (see below).
  - `(app)/organizations/new/` — create-workspace form.
  - `(app)/settings/` — **personal** account settings (`profile`, `security`, `appearance`),
    deliberately outside `(app)/w/[workspaceId]/`: none of these vary by, or reset on, an
    organization switch, so the route itself carries no `workspaceId`. See
    `PersonalSettingsShell` (`frontend/src/features/settings/personal-settings-shell.tsx`).
  - `(app)/w/[workspaceId]/` — the per-workspace shell (topbar, tenant selector) and, at
    its index, the Workbench itself. `settings/` here is **organization** settings only
    (`organization`, `members`, `regional`, `reports`, `danger`) — see `SettingsShell`
    (`frontend/src/features/settings/settings-shell.tsx`). The three former
    `w/[workspaceId]/settings/{profile,security,appearance}` routes now redirect to their
    `(app)/settings/*` equivalent for old links/bookmarks.

`frontend/src/proxy.ts` is Next.js 16's renamed `middleware.ts` — confirmed by
[`frontend/AGENTS.md`](../../frontend/AGENTS.md), which exists specifically to warn that
this version has breaking changes from what a model's training data would expect. It does
cheap, optimistic cookie-presence gating before the `(app)/layout.tsx` server check
actually verifies the session; it is not itself the authorization boundary.

## Post-login tenant resolution

`(app)/page.tsx` calls `resolveTenantLanding()` (`frontend/src/lib/tenancy/resolve.ts`), a
pure, unit-tested function with no framework dependency, branching on the caller's
workspace memberships and a remembered-workspace cookie:

- Zero workspaces → onboarding screen (create the first workspace).
- One active workspace → redirect straight into it.
- A remembered workspace that's still valid → redirect into it.
- Otherwise → a tenant chooser.
- A remembered-but-deactivated workspace is explained, not silently dropped.

## The Workbench feature module

`frontend/src/features/workbench/` is the core product surface: a chat composer, a
run-analysis/investigation-progress view, chart rendering, artifact and saved-report
panels, and a memory inspector (developer-mode only). Submitting a question calls
`analyticsApi.createRun()` (`frontend/src/lib/api/analytics.ts`) —
`POST /api/v1/workspaces/{workspaceId}/analytics/runs` — and progress streams back over
Server-Sent Events consumed by `useRunStream` (`hooks/use-run-stream.ts`). This is the
route the chat UI actually calls; the separate, simpler `POST
/api/v1/workspaces/{workspaceId}/agent/run` endpoint exists in the backend but is not
what the Workbench UI uses.

Charts are rendered with **Recharts** (`ChartRenderer`,
`features/workbench/components/chart-renderer.tsx`) against the exact `ChartSpec` type the
backend also uses to rasterize the same chart into a PDF/DOCX with Matplotlib — see
[data-analysis.md](data-analysis.md) and [reporting.md](reporting.md) for the shared
contract and the two independent rendering paths.

## API client and the OpenAPI codegen pipeline

`frontend/src/lib/api/client.ts` is a hand-written `fetch` wrapper (`request<T>()`), not a
generated client: it sends `credentials: "include"` on every call and attaches the
`X-CSRF-Token` header from the `csrf_token` cookie on mutating methods (see
[authentication-and-tenancy.md](authentication-and-tenancy.md) for why). Domain-specific
modules (`analytics.ts`, `auth.ts`, `workspaces.ts`, `saved-reports.ts`, etc.) call
`request()` with typed endpoints.

**Types are generated, the client is not.** `frontend/src/types/api.generated.ts` is
produced by `npm run gen:api`
(`cd ../backend && .venv/bin/python -m scripts.dump_openapi && openapi-typescript
openapi.json -o src/types/api.generated.ts`) — it carries a "do not make direct changes"
header and is checked for staleness against the live backend schema by
`backend/tests/contracts/test_openapi_snapshot.py`. `frontend/src/types/api.ts` is a
hand-written aliasing layer on top of it, correcting one FastAPI/JSON-Schema quirk
(optional-with-a-default fields show up as merely optional) and re-exporting ~90 readable
type aliases (`ChartSpec`, `AnalystRun`, `Workspace`, ...).

## Testing

**Vitest** with `@testing-library/react` and `jsdom` (`frontend/test/setup.ts`); 47 test
files, all colocated next to their source under `src/`. There is no end-to-end test tool
(Playwright/Cypress) anywhere in the repository — component/unit coverage plus the
backend's own OpenAPI-snapshot contract test are what stand in for integration coverage
across the frontend/backend boundary.

## Known limitations

- No API routes of its own and no server-side data layer beyond the auth-gate checks in
  `(app)/layout.tsx` — every domain operation is a client-triggered call to the backend.
- No end-to-end browser test coverage exists; correctness across the full stack relies on
  the OpenAPI snapshot test plus each side's own unit tests.
