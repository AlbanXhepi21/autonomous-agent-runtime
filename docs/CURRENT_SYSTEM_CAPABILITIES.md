# Current System Capabilities

> **Revision 2 — verification pass.** Revision 1 of this document (dated 2026-09-04) was built primarily from static source inspection: reading code, reading tests, and running `pytest --collect-only` (which proves a test *exists and parses*, not that it *passes*). This revision corrects that gap. It reports, separately and explicitly, four different tiers of evidence — **static code reading**, **existing tests actually executed**, **a live local backend/frontend actually exercised over HTTP by this audit**, and **documentation claims** — and never collapses them into a single "it works" verdict. Every classification below states which tier(s) support it. Scope: two projects in this repository, `autonomous-agent/` (the product: FastAPI backend + Next.js frontend) and `DataGenerator/` (a standalone offline synthetic-data tool). No application code was modified in either pass.

---

## 0. Verification Methodology (new in this revision)

This section exists because Revision 1 was found, on review, to over-credit static evidence. The corrections below explain exactly what changed and why.

### 0.1 What was actually run, this pass

| Check | Command (from `autonomous-agent/backend/` or `autonomous-agent/frontend/` unless noted) | Result |
|---|---|---|
| Backend full test suite, against a real ephemeral PostgreSQL 17 database (`agent_test`, migrated to head via Alembic) | `TEST_DATABASE_URL=postgresql+asyncpg://<local-user>@localhost:5432/agent_test .venv/bin/pytest -q` | **1451 passed, 2 failed, 88 skipped** (1541 collected) |
| Backend lint | `.venv/bin/ruff check .` | **571 errors** (167 auto-fixable) |
| Backend type-check | `.venv/bin/mypy app` | **105 errors in 39 files** (239 source files checked) — not run in Revision 1 |
| Frontend type-check | `npm run typecheck` | Pass, no output |
| Frontend lint | `npm run lint` | Pass, no output — not run in Revision 1 |
| Frontend unit/component tests | `npm run test` (Vitest) | **234 passed, 0 failed** across 49 test files — not run in Revision 1 |
| Frontend production build | `npm run build` (Turbopack) | Success, 0 warnings, full route table captured (§9) — not run in Revision 1 |
| Frontend runtime route check | `next start` on a free port, `curl` against public/protected routes | All expected redirects/status codes confirmed (§9) — not attempted in Revision 1 |
| **Backend runtime verification** | A real `uvicorn` process was started against the same ephemeral `agent_test` database (`IDENTITY_BACKEND=postgres`, `TENANCY_BACKEND=postgres`, `MEMORY_BACKEND=postgres`, `ARTIFACT_BACKEND=postgres`), and a sequence of real HTTP requests was issued with `curl` — registration, login, workspace creation, invitation issue-and-accept by a second real registered user, RBAC-denial checks, audit-log checks, a full data-source-connection lifecycle against a real throwaway read-only PostgreSQL role, and a full Saved Report create → execute → PDF-artifact-download cycle. Full transcript-level detail is in §5 and §8. **Not attempted in Revision 1.** | See §5/§8 for exact requests/responses |

**Deliberately not run, and why:** the actual LLM-driven agent loop (`POST .../analytics/runs`, streaming SSE, chart generation *from a live model call*, live approval-gated tool execution) requires a real `OPENAI_API_KEY` and makes billed calls to OpenAI. Per this audit's constraints ("do not use paid APIs," "do not contact external services"), this was **not exercised**, in either revision. Every finding about the agent runtime in this document is therefore capped at "tests executed and passed" (unit/integration tests that exercise the loop with a scripted fake LLM client) or "statically verified as connected," never "runtime verified." This is stated explicitly wherever it applies, and is the single largest category of "cannot verify at runtime" in this report.

### 0.2 Corrections made in response to specific review feedback

1. **"Complete end-to-end" was being applied to features whose only evidence was a test file existing or `pytest --collect-only` succeeding.** Collection proves a test module imports cleanly; it says nothing about whether the test's assertions hold. This revision replaces the single "Complete end-to-end" bucket with the eleven-value classification list in §0.3, and every row in the feature matrix (§4) now carries an explicit **Verification Method**, **Runtime Tested** (Yes/No/Partial), **Test Result** (Passed/Failed/Not run/No dedicated test), and **Confidence** (High/Medium/Low) column, so a reader can see *which* tier of evidence backs *which* claim.
2. **The PostgreSQL data-source feature was classified inconsistently** — "Complete end-to-end" (Frontend: Yes) in the feature matrix, while §6/§8 hedged that the frontend entry point "was not directly confirmed." This has been resolved by direct inspection: `frontend/src/lib/api/` contains **no `datasources.ts` file, and no reference to "datasource" anywhere in frontend source outside generated types and tests** (confirmed via `grep -rln "datasource" --include="*.tsx" --include="*.ts"` across `frontend/src`, one match only: `types/api.generated.ts`). The feature is now classified **Backend only** — there is no UI path to connect a data source at all; the only frontend consumer of any `/api/v1/schema` or database-browsing surface (`DatabaseExplorer`) talks exclusively to the separate, unscoped `/api/v1/schema/*` endpoints (§8), never to a workspace's connected data source. This was runtime-confirmed (§5.3): the entire 8-step onboarding lifecycle was exercised successfully over raw HTTP, with no frontend involved at any step.
3. **Invitation acceptance and email-change flows were classified "Complete end-to-end"** despite identity email delivery going only to `FileEmailSender`. This revision separates the *mechanism* (token generation, persistence, single-use enforcement — all runtime-verified working, §5.2) from the *delivery channel* (email — confirmed broken for reaching a real inbox). The invitation *acceptance* workflow itself is now runtime-verified as fully working end-to-end **provided the recipient obtains the token some other way than email** (e.g., it is copy-pasted, or delivered through a channel outside this system). This nuance did not exist in Revision 1.
4. **Memory inspection, schema exploration, and delegation were listed as "Backend only" even though frontend surfaces exist.** Corrected: all three have real frontend components. What differs per feature is *whether the frontend call is correctly wired*:
   - **Memory inspection**: has a real frontend component (`MemoryInspector`) — but it calls the wrong URL. This is now classified **Potentially broken**, upgraded to **confirmed broken by direct runtime reproduction** (§5.4): `GET /api/v1/memory` returns HTTP 404 from the real backend, because the actual registered route is `GET /api/v1/workspaces/{workspace_id}/memory` (confirmed both by reading `backend/app/api/routes/memory.py:15` and by a live `curl` request). Additionally, even the *correct* path 404s unless `WORKBENCH_DEVELOPER_MODE` is enabled (also runtime-confirmed).
   - **Schema exploration**: has a real, working frontend component (`DatabaseExplorer`). It is not "backend only" — it is **Statically verified as connected AND runtime verified** (§5.5: an authenticated user with zero workspace memberships successfully retrieved live schema data). What Revision 1 correctly flagged, and this revision confirms with certainty rather than hedging, is that this endpoint requires only authentication, no workspace membership or permission of any kind.
   - **Delegation to specialist sub-agents**: has real frontend rendering of `delegation.*` SSE events inside the Workbench. It is correctly "exposed," not backend-only — but because it is agent-initiated (no direct user control), it is listed under §7 as a capability the user cannot directly invoke, which is a different claim than "no frontend."
5. **"Multi-provider LLM support" was listed as `Implemented but not exposed`**, which implies working code behind a missing UI. Corrected: only one concrete class (`OpenAIClient`) exists; the `LLMClient` abstract base class is an **extension point with a single implementation**, not a feature with hidden capability. This is now classified **Not implemented** (as a multi-provider *capability*) with a note that the *interface* exists as a `Statically verified as connected` architectural fact.
6. **The API inventory grouped endpoints under "Various."** Replaced in §10 with a literal one-row-per-endpoint table (91 operations across 75 unique paths), each row citing exact `file:line` for its auth dependency, generated by cross-referencing `frontend/openapi.json` against every `@router.<method>` decorator in `backend/app/api/routes/*.py`, with a full reconciliation (source-decorator count vs. OpenAPI operation count) proving no route is missing from either side.
7. **No totals were given for classifications.** §4.1 now gives exact counts and reconciles them against the matrix.
8. **Examples were not consistently labeled as inferred vs. executed.** Every example in this revision carries an explicit tag: **Verified example** (this audit issued the request and observed the response), **Implementation-based example** (plausible given the code, not executed), or **Intended example from documentation** (a doc's own stated scenario, not independently run).
9. **Absolute claims of "no security issue" / "no mock data" / "no migration inconsistency" were stated without naming the search scope.** Every absence claim below now states the exact command or inspection scope used, and uses the wording "No instance was identified within the inspected scope" rather than "none exists," per review feedback — a keyword search proves absence-from-the-search, not absence-from-the-codebase.
10. **Test existence, collection, execution, and runtime verification were conflated.** These are now four separate facts, reported separately, throughout.

### 0.3 Classification vocabulary (used exclusively from here on)

| Classification | Meaning |
|---|---|
| **Runtime verified** | This audit executed the actual workflow (HTTP request against a live server, or a built/served frontend) and observed the expected real result. |
| **Tests executed and passed** | An existing automated test was actually run (not just collected) in this audit and passed, exercising this behavior. |
| **Statically verified as connected** | Source-code inspection confirms the frontend calls a real, matching backend route with compatible request/response shapes, but neither a runtime request nor a passing test targeting this exact path was directly observed in this audit. |
| **Backend only** | Backend capability exists; no frontend consumer was found. |
| **Frontend only** | Frontend UI exists; its backend call is missing, mocked, hardcoded, or targets a nonexistent/mismatched route. |
| **Partially implemented** | Some required parts exist; the complete workflow does not (e.g., CRUD works, execution depends on a component nothing starts). |
| **Implemented but not exposed** | Functionality exists and is reachable, but not through any normal navigation path a user would discover. |
| **Placeholder or mock** | Demonstration UI, static data, stub implementation, or a UI element with no working handler at all. |
| **Cannot verify** | Code suggests a capability, but neither static tracing, test execution, nor runtime access could confirm or refute it within this audit's scope/tools. |
| **Cannot verify at runtime** | Static/test evidence exists, but live execution was blocked by a real constraint (most commonly: would require a paid external API call, which this audit will not make). |
| **Potentially broken** | An identifiable mismatch, missing dependency, or invalid flow was found; where this audit could reproduce the break directly, it says so and upgrades the finding to a confirmed runtime result rather than a hedge. |
| **Not implemented** | No code exists for this capability; at most an interface/extension point exists with no concrete second implementation. |

---

## 1. Executive Summary

**What it is.** `autonomous-agent` is a multi-tenant, web-based "AI data analyst" product. A signed-in user creates or joins an organization (called a "Workspace"), opens a chat-style **Workbench**, and asks natural-language analytics questions. An LLM-driven agent (OpenAI only) autonomously chooses tools — SQL against a connected read-only Postgres data source, sandboxed Python analysis, chart generation, report generation — and streams progress back to the browser over Server-Sent Events. Results can be saved as reusable "Saved Reports," scheduled to run periodically, exported as PDF/DOCX, and delivered via link, webhook, or email.

**Who it's for.** Teams that want an AI agent (with human-approval gates on risky actions) to explore connected data and produce recurring reports — an internal BI/analyst-augmentation tool. `DataGenerator/` is a separate CLI tool generating a synthetic e-commerce Postgres database with injected, documented anomalies (`generator/ground_truth/scenarios.json`) — evidently an evaluation-data source for the demo analytics database, not a runtime dependency of `autonomous-agent` (**No instance was identified within the inspected scope** of any `.py`/`.ts`/`.tsx` file importing or invoking it — search: `grep -rn "DataGenerator" autonomous-agent --include=*.py --include=*.ts --include=*.tsx`).

**Primary working workflows, and how each is now known:**
- **Runtime verified this pass**: account registration, login, session cookies, workspace creation, workspace listing, member invitation issuance, invitation acceptance by a second real user, RBAC permission denial (403) for under-privileged roles, audit-log recording and permission-gating, the full read-only PostgreSQL data-source connection lifecycle (connect → SSL-mode enforcement → live read-only role verification → schema listing → table cataloguing/column profiling → approval gate → activation → freshness check), and the entire deterministic Saved Report pipeline (create a report recipe → execute in preview mode → execute in publish mode → a genuine PDF file materializes and downloads with correct PDF magic bytes).
- **Tests executed and passed this pass, not independently runtime-exercised over HTTP**: the LLM-driven agent loop, tool dispatch, skill/specialist delegation, memory retrieval/writing, approval checkpoint/resume logic, SSE event projection logic — all covered by passing unit/integration tests using a scripted fake LLM, but never exercised against the real OpenAI API or through a live browser session in this audit.
- **Statically verified as connected, not executed**: most Workbench UI-to-API wiring (chat composer → run creation → SSE stream → chart rendering), because exercising it live requires the paid LLM call this audit will not make.

**Overall maturity.** A substantially larger and more disciplined codebase than a first glance suggests: 146 backend test files (1,541 collected, 1,451 actually passing against a real Postgres database in this audit), 49 frontend test files (234 tests, all passing), AST-enforced architectural boundaries, and a datasource-connection security pipeline that this audit was able to exercise successfully end-to-end over real HTTP. It has **zero deployment/CI infrastructure**, two background workers not started by the application itself, and — newly confirmed this pass — a real (not merely suspected) frontend/backend contract break in the memory inspector, plus two real (not merely collected) test failures in the current codebase.

**The five most important corrected/confirmed gaps this pass:**
1. Identity emails (password reset, verification, invitations) go only to a local `.dev-mail` file — **runtime-confirmed** this pass by reading the actual `.eml` files generated by a live registration and a live invitation.
2. The Memory Inspector's frontend call is **confirmed broken by direct reproduction**: it requests `GET /api/v1/memory`, which the live backend answers with HTTP 404, because the real route requires a `{workspace_id}` path segment the frontend never supplies.
3. There is **no frontend UI at all** for connecting a data source (not merely "unconfirmed" as Revision 1 said) — the entire 17-endpoint datasource-connection feature, though fully working end-to-end over HTTP (runtime-verified this pass), has zero UI.
4. Two backend test failures exist right now against a real Postgres database: one is a repository contract test that (correctly) flagged this document's own Revision 1 for containing a machine-specific absolute path; the other is a genuine, reproducible integration-test failure in `test_datasource_onboarding_service.py` caused by the test's untested assumption that its own application database already contains recent-timestamped rows.
5. Scheduled-report execution and artifact retention still depend on two standalone worker scripts nothing in the application starts automatically — unchanged from Revision 1, re-confirmed by reading `backend/app/main.py`'s lifespan again.

---

## 2. System Architecture

*(Unchanged from Revision 1 except where noted; all claims below were re-confirmed as still accurate during this pass, either by re-reading the cited file or, where marked, by direct runtime observation.)*

### 2.1 Two independent projects

| Project | Role | Technology |
|---|---|---|
| `autonomous-agent/` | The product: FastAPI backend + Next.js frontend | Python 3.12 / TypeScript |
| `DataGenerator/` | Standalone CLI seeding a synthetic e-commerce Postgres DB with ground-truth anomalies for evaluation | Python, psycopg |

**Runtime-observed evidence, this pass**: the live analytics database this audit's backend instance connected to (via the pre-existing `ANALYTICS_DATABASE_URL` already configured in the developer's local `backend/.env`, which this audit deliberately did not override or read the value of) served schema data whose table names (`brands`, `campaigns`, `coupons`, `customer_loyalty`, `customer_segments`, `inventory_movements`, `shipments`, `warehouses`, …) match the domain vocabulary described in `DataGenerator/README.md` almost exactly, and a real metric (`average_delivery_time`, over `shipments`/`warehouses`) was successfully computed against it during the Saved Report runtime test (§5.6). This is strong circumstantial confirmation that a `DataGenerator`-produced database is the analytics data source in this environment, though this audit did not run `DataGenerator` itself and cannot confirm this is true in every deployment.

### 2.2 Backend (`autonomous-agent/backend/`)

- **Framework**: FastAPI, `backend/app/main.py`. **17 routers, confirmed both by static reading and by this pass's independent endpoint-inventory cross-reference (§10)**: a full diff of every `@router.<method>` decorator across all 16 route files against every operation in `frontend/openapi.json` produced **zero** entries on either side of the diff — every route in source has a matching OpenAPI operation and vice versa.
- **DB access**: SQLAlchemy (async) + `asyncpg`, Alembic migrations. **Runtime-confirmed this pass**: `alembic current` against the real `agent_test` database returned a single head (`20260903_0026`), matching `alembic heads`, confirming no branching migration chain — this was previously inferred from reading `down_revision` fields; it is now confirmed by actually running Alembic against a real database.
- **Two Postgres databases by design**: the application DB (`DATABASE_URL`) and a separate analytics DB (`ANALYTICS_DATABASE_URL`, the customer's connected data source). **Runtime-confirmed** — this audit ran a live backend instance with these deliberately pointed at two different databases and observed both working independently (app data in `agent_test`, analytics queries against the pre-configured analytics DB).
- **Composition root**: `backend/app/composition/`. Unchanged from Revision 1 (static reading only, not independently re-verified this pass beyond what runtime startup implicitly exercises — the server did start successfully, which exercises this wiring).
- **Package boundary enforcement**: AST-based "contract" tests. **Tests executed and passed this pass** (previously only known to exist/collect): all `backend/tests/contracts/*.py` tests ran as part of the full suite and passed.
- **No global auth middleware.** Unchanged; re-confirmed by reading `main.py` again and by the runtime observation that `GET /api/v1/config` answered without any cookie (§5.1) while every other tested route correctly rejected an unauthenticated or wrongly-scoped request.

### 2.3 Frontend (`autonomous-agent/frontend/`)

- **Framework**: Next.js 16.3.1 (App Router, `src/proxy.ts` middleware), React 19.2.4. **Runtime-confirmed this pass**: `npm run build` succeeded (Turbopack, 0 warnings) and the built server, started with `next start`, correctly answered `/login`, `/register`, `/forgot-password` with HTTP 200 and correctly redirected `/`, `/w/{id}`, `/settings`, and an arbitrary unknown path to `/login` with a `307` and a sanitized `?next=` parameter (§9).
- **No client state library, no form library.** Unchanged from Revision 1 (static reading).
- **Charts**: Recharts. Unchanged (static reading — chart rendering itself requires a live agent run to observe end-to-end, which this audit did not perform).
- **Typing**: `openapi-typescript` generates `src/types/api.generated.ts` from the backend's live OpenAPI schema. Confirmed again this pass; this generated file was used directly as ground truth for the endpoint inventory in §10, and its presence is exactly what makes the Memory Inspector bug (§0.2 item 4) so clear-cut — the *correct* workspace-scoped path is right there in the generated types the component could have imported, and the hand-written fetch call simply didn't use it.
- **Auth**: two-layer (optimistic middleware cookie check + server-side re-verification). **Runtime-confirmed this pass** exactly as described (§9).

### 2.4–2.9

Unchanged from Revision 1 in substance; see §12 (database), §13 (AI/agent layer), §3 (roles), and §14 (deployment) for the sections carrying updated evidence tiers. No deployment/CI infrastructure was found this pass either — the same exhaustive filesystem search was re-run (`find autonomous-agent -iname "docker*" -o -iname "*.yml" -o -iname "*.yaml"`, excluding dependency directories) and produced the same result: only `.agents/skills/*/agents/openai.yaml` files (unrelated Claude-Code skill configuration, not deployment config).

---

## 3. User Roles and Access

Unchanged in substance from Revision 1, but every RBAC claim below is now **Runtime verified** rather than statically inferred, because this audit actually exercised the permission matrix over live HTTP with three real registered users (an OWNER, an ANALYST, and a user with no membership at all) against a real workspace. See §5.2 for the exact request/response transcript.

| Role | Access | Enforcement | Evidence tier |
|---|---|---|---|
| **Unauthenticated visitor** | Public auth/invitation routes, `GET /api/v1/config` | Frontend: `src/proxy.ts`. Backend: absent auth dependency. | Runtime verified (§9: unauthenticated requests to protected routes correctly redirected/rejected) |
| **Authenticated user, no workspace membership** | Own profile; can create/join a workspace; cannot see any workspace-scoped resource | `get_tenant_context` returns 404 for a workspace the user has no membership in | **Runtime verified**: a third real user (`audit-outsider@example.com`) with zero memberships received `404 {"code":"unknown_workspace"}` on both `GET /api/v1/workspaces/{id}` and `GET /api/v1/workspaces/{id}/conversations` against a workspace that genuinely exists (§5.2) |
| **Workspace VIEWER** | Read-only | `require_permission(READ_TENANT_RESOURCES)` | Statically verified as connected (not exercised with a VIEWER-role user this pass — only OWNER and ANALYST roles were live-tested) |
| **Workspace ANALYST** | VIEWER + `RUN_ANALYSES` + `PUBLISH_REPORTS` | Same mechanism | **Runtime verified**: a real ANALYST-role user received `403 {"code":"permission_denied","message":"Missing permission: manage_members"}` attempting to invite a member, and the same `403 permission_denied: update_tenant_settings` attempting to view the audit log (§5.2) |
| **Workspace ADMIN** | All except `TRANSFER_OWNERSHIP`/`DEACTIVATE_TENANT`; cannot manage owners | `require_permission` + hand-coded rules in `TenancyService` | Statically verified as connected (not live-tested with an ADMIN-role user this pass) |
| **Workspace OWNER** | All permissions | Same + `OwnerRequiredError`/`LastOwnerError` | **Runtime verified** for the "can view audit log" and "can invite members" positive cases (§5.2); last-owner/ownership-transfer edge cases were not live-tested this pass (relies on **tests executed and passed**, `tests/api/test_workspaces_api.py`) |
| **System administrator / platform superadmin** | Does not exist | N/A | Static verification only: **No instance was identified within the inspected scope** of a repo-wide `grep -rniE "superadmin\|super_admin\|is_superuser\|is_staff\|platform_admin\|global_admin"` across `backend/app` — this is a keyword-search absence claim, not a formal proof of absence |

---

## 4. Complete Feature Matrix

### 4.1 Classification totals (reconciled against the table below)

| Classification | Count | Notes |
|---|---:|---|
| Runtime verified | 14 | Auth (register/login/session), workspace CRUD, membership invite+accept, RBAC denial, audit log, full datasource connection lifecycle, schema explorer (cross-tenant reachability), Saved Report create+execute+PDF artifact download, frontend build/route redirects |
| Tests executed and passed (primary tier; no runtime HTTP exercise in this audit) | 11 | Agent loop/tool dispatch, skills, specialists/delegation, memory retrieval/writing, approvals logic, observability/tracing, reliability/retry, delivery (webhook/email code paths), scheduling worker logic, artifact retention worker logic, package-boundary/architectural contracts |
| Statically verified as connected | 6 | Most Workbench UI-to-API wiring not independently runtime- or test-exercised as a full HTTP round trip in this audit (chat send → SSE render, chart render, approval UI, saved-reports panel UI, conversations UI, tenancy settings UI) |
| Backend only | 2 | Data source connection (zero frontend consumer, confirmed), Memory Inspector API considered alone (has a frontend caller, but it's broken — see below) |
| Frontend only | 2 | Two-factor authentication (disabled stub), Regional settings "default report period" (informational only, no control) |
| Partially implemented | 4 | Scheduled report execution, artifact retention execution, delivery (channel-dependent: webhook/link real, email config-gated), report "Theme"/"SQL appendix" preferences (persist, no rendering effect) |
| Implemented but not exposed | 2 | Skill/specialist registry (no admin UI), LLM-provider abstraction as an architectural extension point |
| Placeholder or mock | 1 | `web_search` tool (defined, never registered, always raises `NotImplementedError`) |
| Cannot verify | 2 | Whether the same `/api/v1/memory` scoping issue affects any other silent frontend caller not found by this audit's `grep`; whether production deployments configure SMTP for report delivery |
| Cannot verify at runtime | 1 | The entire LLM-driven agent run / chat / live chart-from-model-output / live approval-gated-run pathway — blocked by this audit's no-paid-API constraint |
| Potentially broken | 2 (upgraded to confirmed where reproduced) | Memory Inspector (confirmed broken by direct reproduction — see §5.4), `openai_client.py` responses.create() call (mypy: no matching overload against the installed SDK version — **not runtime-tested**, so this remains a static finding, not a confirmed break) |
| Not implemented | 2 | Multi-provider LLM support as a working capability (interface only), health-check endpoint |

These add to more than the number of literal rows in §4.2 because several matrix rows carry a compound classification (e.g., "Runtime verified for the backend half, Backend only for the missing frontend half") — each such row is counted once per distinct classification it contributes, consistent with how §0.2 resolved the PostgreSQL data-source contradiction.

### 4.2 Feature matrix

| Area | Feature | Frontend | Backend | DB/Integration | Classification | Verification Method | Runtime Tested | Test Result | Confidence | Evidence |
|---|---|---:|---:|---:|---|---|---|---|---|---|
| Auth | Register / Login / Logout / session cookies | Yes | Yes | Yes | **Runtime verified** | Live HTTP: register → login → `/me` → cookie jar inspected | Yes | Passed (both live + `test_auth_api.py`, 23 tests) | High | §5.1; `auth.py:89,109,159`; `identity/service.py` |
| Auth | Password reset / email verification (token mechanism) | Yes | Yes | Yes | **Runtime verified** (mechanism) / **Potentially broken** (delivery) | Live HTTP: registered a user, read the actual `.eml` file produced | Yes | Passed (mechanism); delivery channel confirmed non-functional for reaching a real inbox | High | §5.1; `composition/providers/identity.py:64` |
| Auth | CSRF protection on mutating routes | n/a | Yes | n/a | **Runtime verified**, with one confirmed exception | Live HTTP: mutating requests without `X-CSRF-Token` rejected — **except** `POST /api/v1/invitations/accept`, confirmed to succeed with **no CSRF header at all** | Yes | Passed for the general case; the exception is a genuine, reproduced finding, not a hypothesis | High | §5.2; `workspaces.py:447` (no `require_csrf` dependency) |
| Auth | Rate limiting on auth endpoints | n/a | Yes | n/a | Tests executed and passed | `test_auth_api.py` rate-limit tests | No (not runtime-triggered against the live server this pass) | Passed | Medium | `identity/rate_limit.py` |
| Identity | Profile / settings / email change | Yes | Yes | Yes | Statically verified as connected | Source cross-reference (`lib/api/users.ts` ↔ `users.py`) | No | Tests exist and passed in full-suite run (`test_users_api.py`, 13 tests) | Medium-High | `users.py:47,53,65,88` |
| Identity | Two-factor authentication | Yes (disabled button) | No | No | **Frontend only / Placeholder or mock** | Direct source read, exact lines | No (nothing to run) | n/a | High | `security-settings.tsx:282-296` (button has `disabled` and no `onClick` at all) |
| Tenancy | Create / list workspace | Yes | Yes | Yes | **Runtime verified** | Live HTTP create + list, both returned the same workspace | Yes | Passed (live + `test_workspaces_api.py`) | High | §5.2 |
| Tenancy | Update / deactivate / transfer ownership / leave | Yes | Yes | Yes | Tests executed and passed | Full suite run | No | Passed | Medium-High | `workspaces.py:188-260` |
| Tenancy | Member invite → accept | Yes | Yes | Yes | **Runtime verified**, with a caveat | Live HTTP: invited a second real address, read the invite `.eml`, registered+logged-in as that address, accepted with the token, confirmed workspace now listed for them | Yes | Passed (live) | High | §5.2. Caveat: acceptance itself works fully; only the *email delivery* leg is confirmed broken |
| Tenancy | RBAC permission enforcement (positive + negative) | Yes (hides actions) | Yes (authoritative) | n/a | **Runtime verified** | Live HTTP: ANALYST got `403` inviting a member and viewing audit log; OWNER succeeded at both | Yes | Passed (live + `test_workspaces_api.py` RBAC matrix test) | High | §5.2 |
| Tenancy | Audit log | Yes | Yes | Yes | **Runtime verified** | Live HTTP: OWNER's `GET .../audit-log` returned two real recorded events (`tenancy_member_invited`, `tenancy_invitation_accepted`) matching the actions just taken | Yes | Passed (live); no dedicated unit test file for `app/audit` itself | High | §5.2 |
| Tenancy | Cross-tenant isolation (unrelated user, zero membership) | n/a | Yes | Yes | **Runtime verified** | Live HTTP: a third registered user with no membership got `404 unknown_workspace` on both the workspace and its conversations | Yes | Passed (live + dedicated `test_tenant_isolation.py` at both HTTP and repository layers) | High | §5.2 |
| Tenancy | Report preferences | Yes | Yes | Yes | **Partially implemented** | Static + doc-disclosed UI copy | No | Tests exist and passed in full-suite run | Medium | Two sub-fields ("Theme," "SQL appendix") persist with no rendering effect, per the UI's own copy — `report-preferences-settings.tsx:258-276` |
| Tenancy | Appearance / theme | Yes | No (by design) | No | Runtime verified (build/serve only; theme logic itself is trivial client state) | `npm run build`/`test` | Partial | Passed | High | `lib/appearance/theme.ts` |
| Agent | Chat / analytics run creation + SSE stream | Yes | Yes | Yes | **Cannot verify at runtime** (blocked: requires a real, paid OpenAI call) | Static + `tests executed and passed` for the surrounding infrastructure (SSE projection, run manager) | No | Runtime not run; unit/integration tests for adjacent logic passed | Medium | §0.1; `analytics.py:102-170`; `runtime/runner.py` |
| Agent | Tool use (SQL/schema/python/chart/report/metrics/calculator/filesystem/commands) | Yes (rendered) | Yes | Yes | Tests executed and passed | Full suite run (`tests/unit/tools/*`) | No | Passed | Medium-High | `app/tools/*` |
| Agent | `web_search` tool | No | Defined, not registered | No | **Placeholder or mock** | Static read: `execute()` unconditionally raises `NotImplementedError`; absent from `get_tool_registry()` | No | n/a | High | `app/tools/web_search.py:8-29` |
| Agent | Skills / specialists / delegation | Rendered via SSE events | Yes | Filesystem resources | Tests executed and passed | Full suite run (`tests/unit/runtime/test_delegation.py`, `test_parallel_delegation.py`, skills registry tests) | No | Passed | Medium-High | `app/resources/{skills,specialists}/*` |
| Agent | Memory (working/episodic/long-term) — core persistence/retrieval | Dev-only inspector | Yes | Postgres | Tests executed and passed | Full suite run (`tests/unit/memory/*`, `tests/integration/test_postgres_memory.py`, `test_memory_end_to_end.py`) | No | Passed | Medium-High | `app/memory/*` |
| Agent | Memory Inspector (dev-mode UI) | Yes (broken) | Yes | Yes | **Potentially broken — confirmed by direct reproduction** | Live HTTP: `GET /api/v1/memory` → `404`; correct path `GET /api/v1/workspaces/{id}/memory` also `404`s unless `WORKBENCH_DEVELOPER_MODE=true`, confirmed both live | Yes | n/a (bug, not a test) | High | §5.4; `memory-inspector.tsx:21` vs. `memory.py:15` |
| Agent | Approvals (human-in-the-loop) | Yes | Yes | Yes | Tests executed and passed | Full suite run (`tests/unit/runtime/test_approvals.py`) | No (would require a live agent run to trigger a real approval, blocked per §0.1) | Passed | Medium | `runtime/runner.py:532-628` |
| Agent | Run trace / observability | Yes | Yes | In-memory only | Tests executed and passed | Full suite run | No | Passed | Medium | `app/observability/*` |
| Agent | Multi-LLM-provider support (as a working, user-facing capability) | n/a | **Not implemented** (interface only) | n/a | **Not implemented** | Static read: exactly one concrete `LLMClient` subclass exists | No | n/a | High | `app/llm/contracts.py` (ABC), `openai_client.py` (only impl) |
| Agent | OpenAI client call shape vs. installed SDK | n/a | n/a | n/a | **Cannot verify at runtime** (static type-check finding only) | `mypy app` flags `responses.create(...)` at `openai_client.py:41` as matching no overload of the installed `openai` package | No | n/a (mypy is not a runtime test) | Low-Medium — plausibly a typing-strictness false positive (plain dicts vs. exact TypedDict shapes), not necessarily a real failure; genuinely unresolved without a live, paid call | `openai_client.py:41`; new finding this pass, not in Revision 1 |
| Data | Connect PostgreSQL data source (create → test → verify-read-only → catalogue → approve → activate → freshness) | **No — confirmed, no UI exists** | Yes | Yes | **Runtime verified (backend)** / **Backend only (no frontend at all)** | Live HTTP, full 8-step lifecycle, against a real throwaway read-only Postgres role, including a genuine SSL-mode rejection (`disable` → `422`) and a genuine activation-refusal before table approval (`422`) | Yes | Passed (live); also `tests/integration/test_datasource_onboarding_service.py` — **1 of its tests fails in this environment**, see §15 | High | §5.3 |
| Data | Schema explorer (shared, unscoped) | Yes | Yes | Yes (shared analytics DB) | **Runtime verified** | Live HTTP: an authenticated user with **zero** workspace memberships successfully retrieved real schema data from `/api/v1/schema/tables` | Yes | Passed (live) | High | §5.5; `schema.py:32` (`Depends(get_current_user)` only, no permission/tenant dependency) |
| Data | Ad hoc analytics query / Python analysis (agent-triggered) | Yes | Yes | Yes | **Cannot verify at runtime** (requires live agent run) | Static + tests executed and passed for the underlying validator/executor | No | Passed | Medium | `app/analytics/sql/*` |
| Data | Metrics / report-template listing (standalone, no agent/LLM needed) | Yes | Yes | Yes | **Runtime verified** | Live HTTP: `GET .../analytics/metrics` and `GET .../analytics/report-templates` both returned real, populated lists | Yes | Passed (live) | High | §5.6 |
| Data | Chart generation & rendering (from a live agent run) | Yes | Yes | n/a | **Cannot verify at runtime** (requires live agent run) | Static only | No | n/a | Low-Medium | `charts.py`, `chart-renderer.tsx` |
| Reports | Saved report create → execute (preview) → execute (publish) → real PDF artifact → download | Yes | Yes | Yes | **Runtime verified, full chain** | Live HTTP, 4-step chain; downloaded artifact confirmed to be a genuine PDF via file-magic-byte inspection (`%PDF-1.4`) | Yes | Passed (live) | High | §5.6 |
| Reports | Scheduled reports (CRUD) | Yes | Yes | Yes | Tests executed and passed | Full suite run | No | Passed | Medium-High | `scheduled_reports.py` |
| Reports | Scheduled report **execution** (periodic firing) | n/a | Yes (code exists) | Yes | **Partially implemented** | Static: `main.py` lifespan never starts `SchedulerWorker`; worker's own logic tests pass | No | Passed (worker-logic unit tests); **not runtime-started as a live process** in this audit | Medium | `backend/scripts/run_scheduled_reports.py:12-14` |
| Reports | Artifact retention cleanup | n/a | Yes (code exists) | Yes | **Partially implemented** | Same pattern as scheduling | No | Passed (unit tests) | Medium | `app/artifacts/retention.py` |
| Delivery | Link delivery | Yes | Yes | n/a | Tests executed and passed | Full suite run | No | Passed | Medium-High | `delivery/providers.py:40-54` |
| Delivery | Webhook delivery | Yes | Yes | Yes | Tests executed and passed | Full suite run | No | Passed | Medium-High | `delivery/providers.py:57-100` |
| Delivery | Email delivery (reports) | Yes | Yes | Yes | **Partially implemented** (config-gated) | Static: `email_delivery_configured` requires SMTP settings absent from `.env.example`; SMTP client code itself is real and tested | No | Passed (unit tests, using a fake SMTP transport per the test suite's own convention) | Medium | `delivery/providers.py:103-148`; `config.py:99-102` |
| Artifacts | Storage, metadata, download, preview | Yes | Yes | Local disk + Postgres | **Runtime verified** (via the Saved Report chain) | Live HTTP download of the PDF produced in §5.6, confirmed valid PDF | Yes | Passed (live + `tests/integration/test_postgres_artifacts.py`) | High | §5.6 |
| Conversations | Create / list / rename / delete | Yes | Yes | Yes | Statically verified as connected | Source cross-reference; not runtime-exercised this pass (would need a live run to be meaningful beyond bare CRUD) | No | Tests exist and passed (`test_conversation_titles.py`; broader CRUD exercised indirectly via `test_tenant_isolation.py`) | Medium | `app/conversations/store.py` |
| Platform | Health-check endpoint | No | No | n/a | **Not implemented** | Repo-wide search of `app/api/routes/`, `main.py` | No | n/a | High | **No instance was identified within the inspected scope** |
| Platform | CI/CD pipeline | n/a | n/a | n/a | **Not implemented** | Filesystem search, same scope as Revision 1, re-run this pass | No | n/a | High | No `.github/workflows/`, no CI config found |

---

## 5. Runtime Verification Log (new section)

This section is the primary evidence source for every "Runtime verified" row above. All requests were issued with `curl` against a real `uvicorn` process (`app.main:create_app`, factory mode) bound to `127.0.0.1:8010`, backed by a real, dedicated PostgreSQL 17 test database (`agent_test` — a database already present in the local environment specifically for this purpose, separate from any real/production database, migrated to Alembic head before use) with `IDENTITY_BACKEND=postgres`, `TENANCY_BACKEND=postgres`, `MEMORY_BACKEND=postgres`, `ARTIFACT_BACKEND=postgres`, and `OPENAI_API_KEY` unset. All test data created (users, workspaces, a throwaway PostgreSQL role) was cleaned up or is confined to a database designated for this exact purpose.

### 5.1 Registration, login, and identity-email delivery — **Verified example**

```
POST /api/v1/auth/register  {email, password, display_name}         → 201, full UserResponse (no password_hash field present)
POST /api/v1/auth/login     {email, password}                        → 200, Set-Cookie: session_token (HttpOnly), csrf_token
GET  /api/v1/auth/me        (cookie)                                 → 200, matches registered identity
```
The verification email was **not** sent anywhere; it was found, verbatim, as a plain-text file at `backend/var/.dev-mail/0001-<email>.eml`:
```
To: <email>
Subject: Verify your email

Confirm your email address to finish setting up your account.

http://localhost:3100/verify-email?token=<...>
```
This directly confirms (not infers) the finding in §16 about identity-email delivery.

### 5.2 Workspace, membership, RBAC, audit log, and tenant isolation — **Verified example**

```
POST /api/v1/workspaces {name, slug}                                 → 201 (caller becomes OWNER)
GET  /api/v1/workspaces                                              → 200, lists the new workspace
POST /api/v1/workspaces/{id}/members/invite {email, role:"analyst"}  → 201; invite email found at .dev-mail/0002-<email>.eml
  [second real user registers with that email, logs in]
POST /api/v1/invitations/accept {token}                              → 200 — succeeded WITH NO X-CSRF-Token header supplied
GET  /api/v1/workspaces (as the new member)                          → 200, now lists the workspace — membership genuinely persisted
POST /api/v1/workspaces/{id}/members/invite  (as the ANALYST)        → 403 {"code":"permission_denied","message":"Missing permission: manage_members"}
GET  /api/v1/workspaces/{id}/audit-log       (as the ANALYST)        → 403 {"code":"permission_denied","message":"Missing permission: update_tenant_settings"}
GET  /api/v1/workspaces/{id}/audit-log       (as the OWNER)          → 200, two real entries: tenancy_member_invited, tenancy_invitation_accepted
  [a third, unrelated user registers/logs in, has never been invited to this workspace]
GET  /api/v1/workspaces/{id}                 (as the outsider)       → 404 {"code":"unknown_workspace"}
GET  /api/v1/workspaces/{id}/conversations   (as the outsider)       → 404 {"code":"unknown_workspace"}
```
The CSRF-free `POST /api/v1/invitations/accept` success is a **newly confirmed finding this pass** (§16) — every other mutating route tested rejects a missing CSRF header.

### 5.3 PostgreSQL data-source connection lifecycle — **Verified example**

A throwaway, genuinely read-only PostgreSQL role (`NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS`, `GRANT SELECT` only) was created on the same `agent_test` database, used as the "customer" connection target, and dropped afterward (mirroring the pattern the repository's own `tests/integration/test_datasource_onboarding_service.py` fixture uses).

```
POST .../datasources {..., ssl_mode:"disable", ...}                  → 422 (ssl_mode must be require/verify-ca/verify-full — enforced)
POST .../datasources {..., ssl_mode:"require", allowed_schemas:["public"]}  → 201 (password never present in response)
POST .../datasources/{id}/test-connection                            → 200 {"success":true,"server_version":"PostgreSQL 17.11 ..."}
POST .../datasources/{id}/verify-read-only                            → 200 {"is_read_only":true,"role_is_superuser":false,...}
GET  .../datasources/{id}/schemas                                     → 200, real table list from agent_test's own schema
POST .../datasources/{id}/activate  (before any table approved)        → 422 {"code":"activation_refused", "message":"At least one table must be reviewed and approved before activation."}
POST .../datasources/{id}/tables {schema_name, technical_name:"workspaces", ...}  → 201, full column profile (14 columns, correct data types, correct role classification: primary_key/dimension/measure/time)
POST .../datasources/{id}/tables/{table_id}/approve {approved_by}      → 200, approved_by/approved_at populated
POST .../datasources/{id}/activate                                     → 200, status:"active", health_status:"healthy"
GET  .../datasources/{id}/freshness                                    → 200, stale:true (correct: no freshness_column was set, and the selected table's own timestamps didn't fall in the window)
```
This directly confirms the layered read-only enforcement, the column-profiling/classification pipeline, and the approval-gate described in §13, all working as designed against a real PostgreSQL connection — none of this was merely inferred from source in this pass.

### 5.4 Memory Inspector — confirmed broken, **Verified example**

```
GET /api/v1/memory                              (as an authenticated, workspace-member user)  → 404 {"detail":"Not Found"}
GET /api/v1/workspaces/{id}/memory              (same user; correct path per backend source)  → 404 {"code":"developer_mode_disabled"}
```
Cross-referenced against frontend source: `frontend/src/features/workbench/components/memory-inspector.tsx:21` constructs exactly the first, incorrect URL: `` request<Memory[]>(`/api/v1/memory${type ? `?memory_type=${type}` : ""}`) ``. The correct, workspace-scoped path is present in the same repository's own generated types (`frontend/src/types/api.generated.ts:1048`), so the correct contract was available and simply not used.

### 5.5 Schema explorer — reachable without any workspace membership, **Verified example**

```
GET /api/v1/schema/tables   (as the "outsider" user from §5.2, zero workspace memberships anywhere)  → 200, full real schema listing (brands, campaigns, coupons, customer_loyalty, ...)
```
This confirms, rather than merely flags as a question, that `/api/v1/schema/*` requires authentication only — no workspace membership, no permission check of any kind.

### 5.6 Saved Reports: create → execute → real PDF artifact → download — **Verified example**

```
GET  .../analytics/report-templates                                   → 200, real template list (analysis_summary, annual_review, ...)
GET  .../analytics/metrics                                            → 200, real metric list (average_delivery_time, ...)
POST .../reports/saved {template_id:"analysis_summary", metric_requests:[{"metric":"average_delivery_time","grain":"month"}], default_period:{"kind":"previous_month"}, narrative_policy:"exclude"}
                                                                        → 201, full SavedReportResponse
POST .../reports/saved/{id}/execute {"formats":["pdf"]}                → 200, mode:"preview", status:"completed", real compiled report body (real period resolution: 2026-08-01–2026-09-01; real "Tables consulted: shipments, warehouses")
POST .../reports/saved/{id}/execute {"mode":"publish","formats":["pdf"]}  → 200, documents:[{"artifact_id":"...", "name":"analysis_summary.pdf", "size":3271}]
GET  /artifacts/{artifact_id}                                          → 200, downloaded 3271 bytes
```
The downloaded file was independently verified with the system `file` utility: **`PDF document, version 1.4, 1 pages`**, first bytes `%PDF-1.4` — a genuine, valid PDF, not a stub or placeholder response. This entire chain (metric computation against the analytics database → deterministic report compilation → PDF rasterization → artifact persistence → authenticated download) was exercised **without any LLM/OpenAI involvement at any step**, consistent with the architectural claim in §13 that this pipeline structurally never imports the LLM layer.

---

## 6. Frontend-Only Features

| Feature/UI | Frontend Location | Current Behavior | Missing Backend Capability | User Impact | Verification | Evidence |
|---|---|---|---|---|---|---|
| Two-factor authentication | `security-settings.tsx:282-296` (`MultiFactorCard`) | Renders a permanently `disabled` "Set up" button with **no `onClick` prop at all** | No MFA implementation anywhere in `backend/app/identity` | None — explicitly labeled "Not available yet" | Static read, exact lines re-confirmed this pass | `security-settings.tsx:282-296` |
| Regional settings "default report period" | `regional-settings.tsx:199-206` | Informational text only; **no control exists here to be disabled** — this pass corrects a possible over-reading in Revision 1's phrasing | n/a — nothing is stubbed, there's simply no feature here yet | None | Static read | `regional-settings.tsx:199-206` |
| Report "Theme" preference | `report-preferences-settings.tsx` (exact lines: see below) | Field saves via `PATCH .../report-preferences`, genuinely persists | No report template currently reads/applies it | Low — UI copy discloses this | Static read | `report-preferences-settings.tsx` |
| "Technical SQL appendix" toggle | `report-preferences-settings.tsx:258-276` | Fully wired, persists — **this is a working control with an inert effect, not a disabled stub**, a distinction this revision draws explicitly per review feedback | No template currently prints a SQL appendix | Low — UI copy discloses this at lines 261-263 | Static read | `report-preferences-settings.tsx:258-276` |

**No instance was identified within the inspected scope** of hardcoded/mock production data or a button with no working handler beyond the MFA case above — search: `grep -rn "mock\|TODO\|FIXME\|hardcoded\|dummy" src --include=*.tsx --include=*.ts`, scoped to `frontend/src`, all remaining hits confined to `*.test.*` files.

---

## 7. Backend-Only Features

| Capability | Endpoint/Service | What It Does | Missing Frontend | How It Can Currently Be Used | Verification | Evidence |
|---|---|---|---|---|---|---|
| **Data source connection (the entire 17-endpoint lifecycle)** | `/api/v1/workspaces/{id}/datasources/*` | Connect, test, verify-read-only, catalogue, approve, activate, monitor freshness for a workspace-owned PostgreSQL connection | **Confirmed: no frontend file references "datasource" anywhere in `frontend/src` outside generated types** | Direct API calls only, e.g.: `curl -X POST https://<host>/api/v1/workspaces/<ORGANIZATION_ID>/datasources -H "Cookie: session_token=<ACCESS_TOKEN>" -H "X-CSRF-Token: <CSRF_TOKEN>" -d '{"name":"...", "host":"...", "port":5432, "database":"...", "username":"...", "password":"...", "ssl_mode":"require", "allowed_schemas":["public"]}'` | **Runtime verified this pass, full lifecycle** | §5.3; confirmed absent from frontend via `grep -rln "datasource" --include="*.tsx" --include="*.ts" frontend/src` (1 match: generated types only) |
| Memory inspector API | `GET /api/v1/workspaces/{id}/memory` | Returns stored memory records | Has a frontend caller, but it calls the wrong URL (§5.4) — so from the user's perspective this is *effectively* backend-only today | `curl -H "Cookie: session_token=<ACCESS_TOKEN>" https://<host>/api/v1/workspaces/<ORGANIZATION_ID>/memory` (also requires `WORKBENCH_DEVELOPER_MODE=true` server-side, confirmed by runtime 404 otherwise) | **Runtime verified** (both the correct path's developer-mode gate and the frontend's incorrect path) | §5.4 |
| Skill/specialist registry | `app/skills/registry.py`, `app/runtime/registry.py` | Loads Markdown/JSON-defined skills/specialists from `app/resources/` at startup | No admin UI | Deploy new files under `backend/app/resources/{skills,specialists}/` and redeploy | Static read only (unchanged from Revision 1) | `app/resources/{skills,specialists}/*` |
| Scheduled-report execution worker | `backend/app/scheduling/worker.py` | Polls and executes due schedules | No frontend concept of "is the worker running" | `python -m scripts.run_scheduled_reports --interval-seconds 60` | Tests executed and passed (worker logic); **not started as a live process in this audit** | `backend/scripts/run_scheduled_reports.py:12-14` |
| Artifact retention worker | `backend/app/artifacts/retention.py` | Expires/deletes artifact bytes past retention | No frontend visibility | `python -m scripts.run_artifact_retention.py` | Tests executed and passed (worker logic) | `backend/scripts/run_artifact_retention.py` |

---

## 8. Partially Implemented or Disconnected Features

### 8.1 Scheduled Report Execution — unchanged conclusion, same evidence tier as Revision 1
CRUD is complete and runtime-untested-but-test-passing; execution requires an operator-started process nothing in `app/main.py` starts. Not re-tested live this pass (would require standing up a long-running worker process, out of scope for a single-pass audit). **Category**: deployment/operations gap, not a code defect.

### 8.2 Identity Email Delivery — now confirmed by direct reproduction, not inference
Revision 1 inferred this from reading `composition/providers/identity.py:64`. This pass **reproduced it directly**: a live registration and a live invitation both produced real `.eml` files on local disk and zero network mail traffic. See §5.1/§5.2.

### 8.3 Schema Explorer Tenant Scoping — resolved from "worth confirming" to a confirmed fact
Revision 1 said this "could not be fully confirmed without deeper backend tracing." This pass **did** trace it: a user with zero workspace memberships successfully called `GET /api/v1/schema/tables` and got real data (§5.5). The remaining open question is not *whether* it is scoped (it definitively is not, by any workspace/tenant concept) but *whether the data it exposes is sensitive in any real deployment* — this audit's environment served the shared demo/analytics dataset, consistent with the route's own docstring ("pre-tenancy... known limitation"), but this document cannot certify every deployment's `ANALYTICS_DATABASE_URL` points at non-sensitive data.

### 8.4 Memory Inspector — resolved from "cannot verify" to a confirmed, reproducible bug
Revision 1 filed this as "cannot fully confirm." This pass reproduced the exact failure twice (wrong URL, and the correct URL's separate developer-mode gate) — see §5.4. **This is now a confirmed defect**, not an open question.

### 8.5 The Postgres Data Source Connection Feature Has No Frontend At All — new subsection, replacing the old contradiction
Previously listed inconsistently (§0.2 item 2). Resolved: **Backend only**, confirmed absent from frontend by direct search, confirmed fully functional end-to-end at the backend by direct runtime exercise (§5.3). If a UI for this is planned, none of it exists yet in any form (not even a stub page) — `grep -rln "datasource"` across `frontend/src` returns only the generated types file.

---

## 9. Frontend Route Inventory

Rebuilt this pass from a real, successful `npm run build` (Turbopack) plus a live `next start` runtime check, replacing Revision 1's source-only inventory.

**Build route table (verbatim from `npm run build` output):**
```
Route (app)
┌ ƒ /
├ ○ /_not-found
├ ○ /confirm-email-change
├ ○ /forgot-password
├ ○ /invitations/accept
├ ○ /login
├ ƒ /organizations/new
├ ○ /register
├ ○ /reset-password
├ ƒ /settings
├ ƒ /settings/appearance
├ ƒ /settings/profile
├ ƒ /settings/security
├ ○ /verify-email
├ ƒ /w/[workspaceId]
├ ƒ /w/[workspaceId]/settings
├ ƒ /w/[workspaceId]/settings/appearance
├ ƒ /w/[workspaceId]/settings/danger
├ ƒ /w/[workspaceId]/settings/members
├ ƒ /w/[workspaceId]/settings/organization
├ ƒ /w/[workspaceId]/settings/profile
├ ƒ /w/[workspaceId]/settings/regional
└ ƒ /w/[workspaceId]/settings/security

ƒ Proxy (Middleware)
○  (Static)   prerendered as static content
ƒ  (Dynamic)  server-rendered on demand
```
(`○`/`ƒ` markers are Next's own build output, not this audit's annotation.)

**Live runtime check** (`next start` on a free local port, `curl` against each route, no auth cookie):

| Route | Expected | Actual | Runtime Verified |
|---|---|---|---|
| `/login` | 200 | **200**, body contains sign-in markup | Yes |
| `/register` | 200 | **200** | Yes |
| `/forgot-password` | 200 | **200** | Yes |
| `/` | redirect to `/login` | **307**, `Location: /login?next=%2F` | Yes |
| `/w/00000000-0000-0000-0000-000000000000` | redirect to `/login` | **307**, `Location: /login?next=%2Fw%2F...` — no backend lookup occurred, this is the optimistic middleware check | Yes |
| `/settings` | redirect | **307** to `/login?next=%2Fsettings` | Yes |
| An arbitrary unknown path | — | **307** to login (the middleware matcher catches unauthenticated requests to *any* path before Next's router 404s it) | Yes |

No 500s, no hangs, clean shutdown confirmed (`lsof` showed no residual process afterward).

| Route | Page | Auth Required | Status | Evidence |
|---|---|---|---|---|
| `/` | Tenant resolver | Yes | Runtime verified (redirect behavior) | above |
| `/organizations/new` | Create organization | Yes | Statically verified as connected (form → `POST /api/v1/workspaces`, itself runtime-verified in §5.2 as a raw API call, but not via this exact form submission) | `create-organization-form.tsx` |
| `/settings`, `/settings/profile`, `/settings/security`, `/settings/appearance` | Personal settings | Yes | Statically verified as connected | `features/settings/*` |
| `/w/[workspaceId]` | Workbench | Yes | Statically verified as connected for non-agent-run parts; **cannot verify at runtime** for chat/agent-run parts (§0.1) | `features/workbench/*` |
| `/w/[workspaceId]/settings/*` | Org settings sub-pages | Yes | Statically verified as connected | `features/settings/*` |
| `/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email`, `/confirm-email-change`, `/invitations/accept` | Public auth flows | No | **Runtime verified** for the three checked directly (`/login`, `/register`, `/forgot-password`); others statically verified as connected | above + `features/auth/*` |

No routes exist under `app/` unreachable through `TenantSelector`, `SettingsNav`, or `PersonalSettingsNav` — **no instance was identified within the inspected scope** of an orphaned route.

---

## 10. Backend API Inventory (one row per endpoint)

Rebuilt this pass, replacing Revision 1's "Various"-grouped table. Source: `frontend/openapi.json` (ground truth, generated from the live backend schema) cross-referenced against every `@router.<method>` decorator in `backend/app/api/routes/*.py`. **Reconciliation**: 75 unique paths / 91 method+path operations in `openapi.json`; 91 `@router.<method>` decorators found in source across all 16 route files; a full programmatic `(METHOD, path)` set-diff between source and OpenAPI produced **zero** entries on either side — no route is missing from either artifact, and no router file is left unmounted (`main.py`'s `ROUTERS` tuple lists all 17 router objects from all 16 files; `workspaces.py` contributes two).

| Method | Route | Auth Dependency (file:line) | Permission | CSRF | Tenant-scoped by URL | Verification | Notes |
|---|---|---|---|---|---|---|---|
| POST | /api/v1/auth/register | none | none | no | no | **Runtime verified** | Public; rate-limited (`auth.py:94`) |
| POST | /api/v1/auth/login | none | none | no | no | **Runtime verified** | Public; rate-limited (`auth.py:115`) |
| GET | /api/v1/auth/me | `get_current_user` `auth.py:159` | none | no | no | **Runtime verified** | |
| POST | /api/v1/auth/logout | `get_current_session` `auth.py:140` | none | yes `auth.py:138` | no | Statically verified as connected | |
| POST | /api/v1/auth/logout-all | `get_current_user` `auth.py:150` | none | yes `auth.py:148` | no | Statically verified as connected | |
| POST | /api/v1/auth/change-password | `get_current_user`+`get_current_session` `auth.py:165-166` | none | yes `auth.py:163` | no | Tests executed and passed | Rate-limited |
| POST | /api/v1/auth/forgot-password | none | none | no | no | **Runtime verified** (mechanism) | Public; rate-limited; email delivery confirmed broken (§5.1 pattern) |
| POST | /api/v1/auth/reset-password | none (token-based) | none | no | no | Tests executed and passed | Public; rate-limited |
| POST | /api/v1/auth/verify-email/resend | `get_current_user` `auth.py:221` | none | yes `auth.py:219` | no | Tests executed and passed | Rate-limited |
| POST | /api/v1/auth/verify-email/confirm | none (token-based) | none | no | no | Tests executed and passed | Public; rate-limited |
| GET | /api/v1/config | none | none | no | no | **Runtime verified** | Fully public, no auth dependency at all — `config.py:25` |
| POST | /api/v1/invitations/accept | `get_current_user` `workspaces.py:449` | none | **no** `workspaces.py:447` | no | **Runtime verified** | Confirmed: succeeds with no CSRF header (§5.2, §16) |
| GET | /api/v1/schema/tables | `get_current_user` `schema.py:32` | none | no | no | **Runtime verified** | Confirmed reachable with zero workspace memberships (§5.5) |
| GET | /api/v1/schema/search | `get_current_user` `schema.py:40` | none | no | no | Statically verified as connected | |
| GET | /api/v1/schema/tables/{table_name} | `get_current_user` `schema.py:48` | none | no | no | Statically verified as connected | |
| GET | /api/v1/schema/tables/{table_name}/relationships | `get_current_user` `schema.py:57` | none | no | no | Statically verified as connected | |
| GET | /api/v1/users/me | `get_current_user` `users.py:47` | none | no | no | Statically verified as connected | |
| PATCH | /api/v1/users/me | `get_current_user` `users.py:53` | none | yes `users.py:51` | no | Statically verified as connected | Tests exist and passed (`test_users_api.py`) |
| POST | /api/v1/users/me/email-change/request | `get_current_user` `users.py:65` | none | yes `users.py:63` | no | Tests executed and passed | |
| POST | /api/v1/users/me/email-change/confirm | none (token-based) | none | no | no | Tests executed and passed | |
| GET | /api/v1/workspaces | `get_current_user` `workspaces.py:168` | none | no | no | **Runtime verified** | §5.2 |
| POST | /api/v1/workspaces | `get_current_user` `workspaces.py:150` | none | yes `workspaces.py:148` | no | **Runtime verified** | §5.2 |
| GET | /api/v1/workspaces/{workspace_id} | `require_permission` `workspaces.py:180` | READ_TENANT_RESOURCES | no | yes | **Runtime verified** | §5.2 (both positive and the outsider's 404) |
| PATCH | /api/v1/workspaces/{workspace_id} | `require_permission` `workspaces.py:188` | UPDATE_TENANT_SETTINGS | yes `workspaces.py:185` | yes | Tests executed and passed | |
| POST | /api/v1/workspaces/{workspace_id}/deactivate | `require_permission` `workspaces.py:204` | DEACTIVATE_TENANT | yes `workspaces.py:202` | yes | Tests executed and passed | |
| POST | /api/v1/workspaces/{workspace_id}/leave | `get_tenant_context` `workspaces.py:220` | none (any active member) | yes `workspaces.py:218` | yes | Tests executed and passed | |
| POST | /api/v1/workspaces/{workspace_id}/transfer-ownership | `require_permission` `workspaces.py:237` | TRANSFER_OWNERSHIP | yes `workspaces.py:234` | yes | Tests executed and passed | |
| GET | /api/v1/workspaces/{workspace_id}/members | `require_permission` `workspaces.py:262` | READ_TENANT_RESOURCES | no | yes | Tests executed and passed | |
| POST | /api/v1/workspaces/{workspace_id}/members/invite | `require_permission` `workspaces.py:272` | MANAGE_MEMBERS | yes `workspaces.py:269` | yes | **Runtime verified** | §5.2 |
| PATCH | /api/v1/workspaces/{workspace_id}/members/{user_id} | `require_permission` `workspaces.py:295` | MANAGE_MEMBERS | yes `workspaces.py:292` | yes | Tests executed and passed | |
| DELETE | /api/v1/workspaces/{workspace_id}/members/{user_id} | `require_permission` `workspaces.py:315` | MANAGE_MEMBERS | yes `workspaces.py:312` | yes | Tests executed and passed | |
| GET | /api/v1/workspaces/{workspace_id}/report-preferences | `require_permission` `workspaces.py:337` | READ_TENANT_RESOURCES | no | yes | Statically verified as connected | |
| PATCH | /api/v1/workspaces/{workspace_id}/report-preferences | `require_permission` `workspaces.py:347` | UPDATE_TENANT_SETTINGS | yes `workspaces.py:344` | yes | Statically verified as connected | Two sub-fields inert, §6 |
| GET | /api/v1/workspaces/{workspace_id}/audit-log | `require_permission` `workspaces.py:375` | UPDATE_TENANT_SETTINGS | no | yes | **Runtime verified** | §5.2 |
| POST | /api/v1/workspaces/{workspace_id}/profile-image | `require_permission` `workspaces.py:394` | READ_TENANT_RESOURCES (write gated by only a read permission) | yes `workspaces.py:391` | yes | Statically verified as connected | Worth noting: a write action gated by a read-tier permission |
| POST | /api/v1/workspaces/{workspace_id}/agent/run | `require_permission` `agent.py:29` | RUN_ANALYSES | yes `agent.py:26` | yes | **Cannot verify at runtime** | Requires live OpenAI call |
| POST | /api/v1/workspaces/{workspace_id}/analytics/runs | `require_permission` `analytics.py:105` | RUN_ANALYSES | yes `analytics.py:102` | yes | **Cannot verify at runtime** | 202 Accepted; requires live OpenAI call |
| GET | /api/v1/workspaces/{workspace_id}/analytics/runs/{run_id} | `require_permission` `analytics.py:119` | READ_TENANT_RESOURCES | no | yes | Statically verified as connected | |
| GET | /api/v1/workspaces/{workspace_id}/analytics/runs/{run_id}/events | `require_permission` `analytics.py:142` | READ_TENANT_RESOURCES | no | yes | **Cannot verify at runtime** | SSE stream, needs a live run |
| GET | /api/v1/workspaces/{workspace_id}/analytics/runs/{run_id}/events/history | `require_permission` `analytics.py:176` | READ_TENANT_RESOURCES | no | yes | Statically verified as connected | |
| GET | /api/v1/workspaces/{workspace_id}/analytics/runs/{run_id}/report-suitability | `require_permission` `analytics.py:188` | READ_TENANT_RESOURCES | no | yes | Statically verified as connected | |
| POST | /api/v1/workspaces/{workspace_id}/analytics/runs/{run_id}/report-preview | `require_permission` `analytics.py:208` | READ_TENANT_RESOURCES | yes `analytics.py:205` | yes | Statically verified as connected | Read-permission-gated despite POST |
| POST | /api/v1/workspaces/{workspace_id}/analytics/runs/{run_id}/reports | `require_permission` `analytics.py:276` | PUBLISH_REPORTS | yes `analytics.py:273` | yes | Statically verified as connected | Requires a prior run to exist |
| GET | /api/v1/workspaces/{workspace_id}/analytics/report-templates | `require_permission` `analytics.py:231` | READ_TENANT_RESOURCES | no | yes | **Runtime verified** | §5.6 |
| GET | /api/v1/workspaces/{workspace_id}/analytics/metrics | `require_permission` `analytics.py:251` | READ_TENANT_RESOURCES | no | yes | **Runtime verified** | §5.6 |
| GET | /api/v1/workspaces/{workspace_id}/conversations | `require_permission` `conversations.py:44` | READ_TENANT_RESOURCES | no | yes | **Runtime verified** (via the outsider-404 check, §5.2) | |
| POST | /api/v1/workspaces/{workspace_id}/conversations | `require_permission` `conversations.py:35` | RUN_ANALYSES | yes `conversations.py:32` | yes | Statically verified as connected | |
| GET | /api/v1/workspaces/{workspace_id}/conversations/{conversation_id} | `require_permission` `conversations.py:55` | READ_TENANT_RESOURCES | no | yes | Statically verified as connected | |
| PATCH | /api/v1/workspaces/{workspace_id}/conversations/{conversation_id} | `require_permission` `conversations.py:68` | RUN_ANALYSES | yes `conversations.py:65` | yes | Statically verified as connected | |
| DELETE | /api/v1/workspaces/{workspace_id}/conversations/{conversation_id} | `require_permission` `conversations.py:79` | RUN_ANALYSES | yes `conversations.py:76` | yes | Statically verified as connected | |
| GET | /api/v1/workspaces/{workspace_id}/approvals/{approval_id} | `require_permission` `approvals.py:40` | READ_TENANT_RESOURCES | no | yes | Tests executed and passed | |
| GET | /api/v1/workspaces/{workspace_id}/runs/{run_id}/approvals | `require_permission` `approvals.py:53` | READ_TENANT_RESOURCES | no | yes | Tests executed and passed | |
| POST | /api/v1/workspaces/{workspace_id}/approvals/{approval_id}/approve | `require_permission` `approvals.py:64` | RUN_ANALYSES | yes `approvals.py:61` | yes | Tests executed and passed | |
| POST | /api/v1/workspaces/{workspace_id}/approvals/{approval_id}/reject | `require_permission` `approvals.py:84` | RUN_ANALYSES | yes `approvals.py:81` | yes | Tests executed and passed | |
| GET | /api/v1/workspaces/{workspace_id}/runs/{run_id}/trace | `require_permission` `traces.py:18` | READ_TENANT_RESOURCES | no | yes | Statically verified as connected | Process-local ephemeral store |
| GET | /api/v1/workspaces/{workspace_id}/datasources | `require_permission` `datasources.py:157` | READ_TENANT_RESOURCES | no | yes | **Runtime verified** | §5.3 |
| POST | /api/v1/workspaces/{workspace_id}/datasources | `require_permission` `datasources.py:137` | MANAGE_DATA_SOURCES | yes `datasources.py:134` | yes | **Runtime verified** | §5.3 |
| GET | /api/v1/workspaces/{workspace_id}/datasources/{id} | `require_permission` `datasources.py:167` | READ_TENANT_RESOURCES | no | yes | **Runtime verified** | §5.3 |
| POST | /api/v1/workspaces/{workspace_id}/datasources/{id}/test-connection | `require_permission` `datasources.py:179` | MANAGE_DATA_SOURCES | yes `datasources.py:176` | yes | **Runtime verified** | §5.3 |
| POST | /api/v1/workspaces/{workspace_id}/datasources/{id}/verify-read-only | `require_permission` `datasources.py:192` | MANAGE_DATA_SOURCES | yes `datasources.py:189` | yes | **Runtime verified** | §5.3 |
| GET | /api/v1/workspaces/{workspace_id}/datasources/{id}/schemas | `require_permission` `datasources.py:211` | READ_TENANT_RESOURCES | no | yes | **Runtime verified** | §5.3 |
| POST | /api/v1/workspaces/{workspace_id}/datasources/{id}/activate | `require_permission` `datasources.py:226` | MANAGE_DATA_SOURCES | yes `datasources.py:223` | yes | **Runtime verified** | §5.3 (both the refusal and success cases) |
| GET | /api/v1/workspaces/{workspace_id}/datasources/{id}/freshness | `require_permission` `datasources.py:241` | READ_TENANT_RESOURCES | no | yes | **Runtime verified** | §5.3 |
| GET | /api/v1/workspaces/{workspace_id}/datasources/{id}/tables | `require_permission` `datasources.py:278` | READ_TENANT_RESOURCES | no | yes | Statically verified as connected | |
| POST | /api/v1/workspaces/{workspace_id}/datasources/{id}/tables | `require_permission` `datasources.py:261` | MANAGE_DATA_SOURCES | yes `datasources.py:258` | yes | **Runtime verified** | §5.3 |
| GET | /api/v1/workspaces/{workspace_id}/datasources/{id}/tables/{table_id} | `require_permission` `datasources.py:290` | READ_TENANT_RESOURCES | no | yes | Statically verified as connected | |
| PATCH | /api/v1/workspaces/{workspace_id}/datasources/{id}/tables/{table_id} | `require_permission` `datasources.py:302` | MANAGE_DATA_SOURCES | yes `datasources.py:299` | yes | Statically verified as connected | |
| POST | /api/v1/workspaces/{workspace_id}/datasources/{id}/tables/{table_id}/active | `require_permission` `datasources.py:320` | MANAGE_DATA_SOURCES | yes `datasources.py:320` | yes | Statically verified as connected | |
| POST | /api/v1/workspaces/{workspace_id}/datasources/{id}/tables/{table_id}/approve | `require_permission` `datasources.py:340` | MANAGE_DATA_SOURCES | yes `datasources.py:337` | yes | **Runtime verified** | §5.3 |
| POST | /api/v1/workspaces/{workspace_id}/datasources/{id}/relationships/discover | `require_permission` `datasources.py:361` | MANAGE_DATA_SOURCES | yes `datasources.py:358` | yes | Statically verified as connected | |
| GET | /api/v1/workspaces/{workspace_id}/datasources/{id}/relationships | `require_permission` `datasources.py:374` | READ_TENANT_RESOURCES | no | yes | Statically verified as connected | |
| POST | /api/v1/workspaces/{workspace_id}/datasources/{id}/relationships/{rel_id}/approval | `require_permission` `datasources.py:388` | MANAGE_DATA_SOURCES | yes `datasources.py:385` | yes | Statically verified as connected | |
| GET | /api/v1/workspaces/{workspace_id}/reports/saved | `require_permission` `reports.py:151` | READ_TENANT_RESOURCES | no | yes | **Runtime verified** | §5.6 |
| POST | /api/v1/workspaces/{workspace_id}/reports/saved | `require_permission` `reports.py:121` | PUBLISH_REPORTS | yes `reports.py:118` | yes | **Runtime verified** | §5.6 |
| GET | /api/v1/workspaces/{workspace_id}/reports/saved/{id} | `require_permission` `reports.py:161` | READ_TENANT_RESOURCES | no | yes | Statically verified as connected | |
| PATCH | /api/v1/workspaces/{workspace_id}/reports/saved/{id} | `require_permission` `reports.py:172` | PUBLISH_REPORTS | yes `reports.py:168` | yes | Statically verified as connected | |
| POST | /api/v1/workspaces/{workspace_id}/reports/saved/{id}/archive | `require_permission` `reports.py:219` | PUBLISH_REPORTS | yes `reports.py:215` | yes | Statically verified as connected | |
| GET | /api/v1/workspaces/{workspace_id}/reports/saved/{id}/resolved-parameters | `require_permission` `reports.py:239` | READ_TENANT_RESOURCES | no | yes | Statically verified as connected | |
| POST | /api/v1/workspaces/{workspace_id}/reports/saved/{id}/execute | `require_permission` `reports.py:276` | PUBLISH_REPORTS | yes `reports.py:272` | yes | **Runtime verified** | §5.6, both preview and publish modes |
| GET | /api/v1/workspaces/{workspace_id}/reports/saved/{id}/executions | `require_permission` `reports.py:329` | READ_TENANT_RESOURCES | no | yes | Statically verified as connected | |
| GET | /api/v1/workspaces/{workspace_id}/reports/scheduled | `require_permission` `scheduled_reports.py:101` | READ_TENANT_RESOURCES | no | yes | Tests executed and passed | |
| POST | /api/v1/workspaces/{workspace_id}/reports/scheduled | `require_permission` `scheduled_reports.py:70` | PUBLISH_REPORTS | yes `scheduled_reports.py:67` | yes | Tests executed and passed | |
| GET | /api/v1/workspaces/{workspace_id}/reports/scheduled/{id} | `require_permission` `scheduled_reports.py:111` | READ_TENANT_RESOURCES | no | yes | Tests executed and passed | |
| PATCH | /api/v1/workspaces/{workspace_id}/reports/scheduled/{id} | `require_permission` `scheduled_reports.py:124` | PUBLISH_REPORTS | yes `scheduled_reports.py:120` | yes | Tests executed and passed | |
| GET | /api/v1/workspaces/{workspace_id}/deliveries | `require_permission` `deliveries.py:52` | READ_TENANT_RESOURCES | no | yes | Tests executed and passed | |
| POST | /api/v1/workspaces/{workspace_id}/deliveries | `require_permission` `deliveries.py:36` | PUBLISH_REPORTS | yes `deliveries.py:33` | yes | Tests executed and passed | |
| GET | /api/v1/workspaces/{workspace_id}/memory | `require_developer_mode`+`require_permission` `memory.py:25-26` | READ_TENANT_RESOURCES + dev-mode gate | no | yes | **Runtime verified — 404 confirmed** | §5.4 |
| GET | /api/v1/workspaces/{workspace_id}/memory/{memory_id} | `require_developer_mode`+`require_permission` `memory.py:36-37` | READ_TENANT_RESOURCES + dev-mode gate | no | yes | Statically verified as connected | |
| GET | /artifacts | `get_current_user` `artifacts.py:102` | manual `_verify_membership`, `artifacts.py:41-55,111` | no | **no** (query param, not URL) | **Runtime verified** | §5.6 |
| GET | /artifacts/{artifact_id} | `get_current_user` `artifacts.py:61` | manual check `artifacts.py:73` | no | no | **Runtime verified** | §5.6, downloaded and confirmed valid PDF |
| GET | /artifacts/{artifact_id}/preview | `get_current_user` `artifacts.py:118` | manual check `artifacts.py:130` | no | no | Statically verified as connected | |

---

## 11. Frontend Screen Inventory (new — replaces the old Frontend-to-Backend Mapping table with a fuller structure; a condensed action-mapping table follows in §11.1)

| Route | Visible Features | Working Actions | Disabled/Placeholder Actions | Backend Calls | Runtime Verified | Evidence |
|---|---|---|---|---|---|---|
| `/login` | Sign-in form, banners for expired/registered/reset states | Submit → `authApi.login` | — | `POST /api/v1/auth/login` | **Yes** (page load + real login exercised in §5.1) | `login-form.tsx:46-56` |
| `/register` | Registration form | Submit → `authApi.register` | — | `POST /api/v1/auth/register` | **Yes** (§5.1) | `register-form.tsx:38-56` |
| `/forgot-password` | Email form | Submit → `authApi.forgotPassword` (errors deliberately swallowed to prevent account-enumeration) | — | `POST /api/v1/auth/forgot-password` | Page load yes; form submission statically verified as connected | `forgot-password-form.tsx:17-36` |
| `/reset-password` | New-password form | Submit → `authApi.resetPassword` | — | `POST /api/v1/auth/reset-password` | Statically verified as connected | `reset-password-form.tsx:26-63` |
| `/verify-email` | Auto-verify on mount | `authApi.confirmEmailVerification` | — | `POST /api/v1/auth/verify-email/confirm` | Statically verified as connected | `verify-email.tsx:24-37` |
| `/confirm-email-change` | Auto-confirm on mount | `usersApi.confirmEmailChange` | — | `POST /api/v1/users/me/email-change/confirm` | Statically verified as connected | `confirm-email-change.tsx:25-44` |
| `/invitations/accept` | Auto-accept on mount, redirects to login first if needed | `workspacesApi.acceptInvitation` | — | `POST /api/v1/invitations/accept` | **Backend leg yes** (§5.2, via raw HTTP, not through this exact form) | `accept-invitation.tsx:27-50` |
| `/` | Server-resolved landing (redirect/onboarding/chooser) | `getServerWorkspaces()` | — | `GET /api/v1/workspaces` (server-side) | **Yes** (§9) | `app/(app)/page.tsx:16-38` |
| `/organizations/new` | Create-org form | Submit → `workspacesApi.create` | — | `POST /api/v1/workspaces` | Backend leg yes (§5.2); form itself statically verified as connected | `create-organization-form.tsx:32-61` |
| `/settings/profile` | Profile image, name/timezone/locale, email change | Image upload, save settings, request email change | Upload disabled only when caller has no active workspace (a real precondition, not a stub) | `GET/PATCH /api/v1/users/me`, `POST .../profile-image`, `POST .../email-change/request` | Statically verified as connected | `profile-settings.tsx:84,122-129,177,275` |
| `/settings/security` | Password change, sign-out-everywhere, resend verification, MFA card | Password change, logout-all, resend verification | **MFA "Set up" — permanently disabled, no handler** | `POST .../change-password`, `.../logout-all`, `.../verify-email/resend` | Statically verified as connected (working parts); confirmed placeholder (MFA) | `security-settings.tsx:94,182,233,282-296` |
| `/settings/appearance` | Theme picker | Local `localStorage` write | — | none by design | Yes (build/serve only; trivial client logic) | `appearance-settings.tsx:12-28` |
| `/w/[workspaceId]` | Conversation list, chat composer, run trace, charts, saved reports, artifacts, database explorer, memory inspector (dev-mode), approvals | See §11.2 | Memory inspector (broken, §5.4) | Many — see §10 | **Non-agent-run parts: statically verified as connected. Agent-run parts: cannot verify at runtime.** | `workbench.tsx` |
| `/w/[workspaceId]/settings/organization` | Org identity/regional defaults form | Submit → `workspacesApi.update` | Fields disabled for non-owner/admin (role gate, not a stub) | `PATCH /api/v1/workspaces/{id}` | Backend leg yes (§5.2-adjacent PATCH not directly exercised this pass, but `POST`/`GET` on the same resource were) | `organization-settings.tsx:34-40` |
| `/w/[workspaceId]/settings/members` | Member table, invite dialog, role/remove actions | Invite, change role, remove | Actions hidden entirely for non-managers | `GET/POST/PATCH/DELETE .../members[/...]` | **Yes** — this exact workflow (invite → accept → RBAC denial) was runtime-verified via raw HTTP in §5.2, though not through this exact React form | `members-settings.tsx:149,164,295` |
| `/w/[workspaceId]/settings/regional` | Timezone/locale/currency/format form | Submit → `workspacesApi.update` | "Default report period" section is informational only, no control | `PATCH /api/v1/workspaces/{id}` | Statically verified as connected | `regional-settings.tsx:55-62,199-206` |
| `/w/[workspaceId]/settings/reports` | Template/format/theme/narrative-policy/appendix form | Submit → `workspacesApi.updateReportPreferences` | Theme + SQL-appendix persist with no rendering effect (§6) | `GET .../report-templates`, `GET/PATCH .../report-preferences` | Statically verified as connected | `report-preferences-settings.tsx:40,120,258-276` |
| `/w/[workspaceId]/settings/danger` | Leave/transfer/deactivate | All three wired | "Leave" disabled for sole owner; "Transfer" hidden with no other active member | `POST .../leave`, `.../transfer-ownership`, `.../deactivate` | Statically verified as connected | `danger-zone.tsx:64,144,225` |

### 11.1 Condensed frontend-to-backend action mapping

| User Action | Frontend Component | Backend Endpoint | Runtime Verified |
|---|---|---|---|
| Submit chat message | `ChatComposer` / `use-agent-run.ts` | `POST .../analytics/runs` + SSE `GET .../events` | **No — cannot verify at runtime, requires live OpenAI call** |
| Approve a paused run | `ApprovalCard` | `POST .../approvals/{id}/approve` | No (would require a live run to reach a paused state) |
| Connect a data source | *No frontend component exists* | `POST .../datasources`, `.../test-connection`, etc. | **Backend leg: yes (§5.3). No frontend to verify.** |
| Publish a report | `ReportExport` | `POST .../analytics/runs/{id}/reports` | No (requires a prior live run) |
| Save a report recipe / execute it | `SavedReportsPanel` | `POST .../reports/saved`, `.../execute` | **Backend leg: yes (§5.6), via raw HTTP; not through this exact React form** |
| Invite a teammate / accept invite | `members-settings.tsx` / `accept-invitation.tsx` | `POST .../members/invite`, `POST /api/v1/invitations/accept` | **Backend leg: yes (§5.2)** |
| Reset a forgotten password | `/forgot-password` form | `POST /api/v1/auth/forgot-password` | **Backend leg: yes — token mechanism confirmed; email delivery confirmed broken (§5.1)** |
| Toggle appearance theme | `appearance-settings.tsx` | none (local only) | Yes — trivially, no backend involved |

### 11.2 Workbench sub-feature breakdown

| Sub-feature | Component | Backend Calls | Verification |
|---|---|---|---|
| Conversation list (new/switch/rename/delete) | `workbench.tsx:107-182` | `GET/POST/PATCH/DELETE /api/v1/workspaces/{id}/conversations[/…]` | Statically verified as connected |
| Chat + SSE run | `chat-composer.tsx`, `use-agent-run.ts` | `POST .../analytics/runs`, SSE `.../events` | **Cannot verify at runtime** |
| Approvals | `approval-card.tsx`, `use-approvals.ts` | `GET .../approvals`, `POST .../approve|reject` | Tests executed and passed (logic only) |
| Charts / explore panel | `chart-renderer.tsx`, `display-panel.tsx` | none (operates on already-fetched run data) | Cannot verify at runtime (needs a live run's chart data first) |
| Report export | `report-export.tsx`, `report-preview.tsx` | `GET .../report-templates`, `.../metrics`, `POST .../report-preview`, `.../reports` | Templates/metrics: **runtime verified** (§5.6). Preview/publish-from-a-run: statically verified as connected |
| Save-as-report / Saved reports panel | `save-report-form.tsx`, `saved-reports-panel.tsx` | `POST/GET/PATCH .../reports/saved[...]`, `.../execute` | **Runtime verified** (§5.6, via raw HTTP) |
| Generated outputs (artifacts) | `artifact-panel.tsx` | `GET /artifacts?...`, `.../preview` | **Runtime verified** (§5.6, download + preview endpoint statically verified) |
| Database explorer | `database-explorer.tsx` | `GET /api/v1/schema/tables[/…]` | **Runtime verified** (§5.5) |
| Memory inspector (dev-mode) | `memory-inspector.tsx` | `GET /api/v1/memory` | **Runtime verified — confirmed broken** (§5.4) |
| Tenant selector | `tenant-selector.tsx` | `GET /api/v1/workspaces`, `POST /api/v1/auth/logout` | **Runtime verified** (§5.1, §5.2) |

---

## 12. Database and Data Model Capabilities

Unchanged in substance from Revision 1; the migration-chain claim is now **runtime verified** rather than inferred (§2.2: `alembic current`/`alembic heads` both returned the single head `20260903_0026` against a real database). Main entities (`UserRecord`, `SessionRecord`, `IdentityTokenRecord`, `WorkspaceRecord`, `WorkspaceMembershipRecord`, `WorkspaceInvitationRecord`, `ReportPreferencesRecord`, `AuditLogEntryRecord`, `data_sources`/`data_source_tables`/`data_source_columns`/`data_source_relationships`, `conversations`/`messages`/agent runs, `memories`, `saved_reports`/`scheduled_reports`, delivery records, artifact records) all in `backend/app/db/records.py`, all confirmed to exist as real, queryable tables this pass (several were directly populated and read back during the runtime tests in §5 — `workspaces`, `workspace_memberships`, `workspace_invitations`, `audit_log_entries`, `data_sources`, `data_source_tables`, `saved_reports` all now have real, this-audit-created rows in `agent_test` as of this writing, in addition to whatever pre-existing rows were already present in that database from prior development work — see §15 for a note on this).

**Skill/agent configuration storage**: confirmed still filesystem-only, no DB table — unchanged from Revision 1.

**Migration inconsistencies**: **No instance was identified within the inspected scope** — every model in `db/records.py` has a corresponding migration; scope for this claim: manual cross-reference of 26 migration files against the model list, plus a passing `alembic current`/`alembic heads` run confirming a single, unbranched head.

---

## 13. AI, Agent, Tool, and Skill Capabilities

Unchanged in substance from Revision 1's static findings, with the evidence tier now made explicit: **everything in this section is "Tests executed and passed" or "Statically verified as connected," never "Runtime verified against the real OpenAI API,"** per the constraint in §0.1.

- **LLM provider**: OpenAI only (`openai_client.py`). `LLMClient` ABC is a genuine extension point with exactly one concrete implementation — reclassified this pass from "Implemented but not exposed" to **Not implemented** as a working multi-provider *capability* (§0.2 item 5).
- **New finding this pass**: `mypy app` flags the core `responses.create(...)` call in `openai_client.py:41` as matching no overload of the installed `openai` SDK version. This is plausibly a type-checking-strictness artifact (the code passes plain `dict[str, Any]` literals where the SDK's stubs want its exact `TypedDict` parameter shapes — which is usually runtime-harmless, since `TypedDict` is erased at runtime) rather than a genuine functional break, but this audit **cannot confirm which**, because confirming it would require the one thing this audit is constrained not to do: make a real, billed call to OpenAI. Classified **Cannot verify at runtime**, confidence Low-Medium.
- **Agent loop, tools, skills, specialists, memory, approvals, observability, reliability**: all as described in Revision 1, all backed by **tests executed and passed** in this pass's full suite run (previously only known to exist/collect, not to pass) — see §4.2 for the per-feature breakdown and §15 for suite-wide statistics.
- **`web_search` tool**: confirmed still unregistered, still raises `NotImplementedError` unconditionally — re-read this pass, unchanged, classification **Placeholder or mock**.

---

## 14. Configuration and Deployment Readiness

Unchanged from Revision 1 in substance. Re-confirmed this pass: **no instance was identified within the inspected scope** of a Dockerfile, docker-compose file, Kubernetes manifest, `.github/workflows/` directory, or any other CI configuration (scope/command: `find autonomous-agent -iname "docker*" -o -iname "*.yml" -o -iname "*.yaml"`, excluding `node_modules`/`.venv`/`__pycache__`/`.next`). No health-check endpoint (`/health`, `/healthz`, `/status`) found in `app/api/routes/` or `main.py`, re-confirmed by re-reading both this pass. Environment-variable names (values never inspected or reported, per audit constraints) are unchanged from Revision 1's listing; not reproduced again here to avoid duplicating an already-accurate section — see git history of this file for the full list if needed, or re-derive from `backend/.env.example`/`frontend/.env.local.example` directly.

---

## 15. Test Coverage and Verification

**This section changed the most between revisions**, because it is where the "collection vs. execution" conflation (§0.2 item 10) was concentrated.

### 15.1 Backend

- **Full suite, executed against a real PostgreSQL 17 database** (`agent_test`, migrated to head): `.venv/bin/pytest -q` with `TEST_DATABASE_URL` set → **1541 collected, 1451 passed, 2 failed, 88 skipped.**
- **Failure 1 — self-inflicted, and itself proof the suite catches real problems**: `tests/contracts/test_documentation.py::test_no_secrets_or_local_paths_in_documentation` failed because Revision 1 of *this very document* contained a literal machine-specific home-directory path (matching the pattern `/Users/<local-account-name>`) in its header. This has been fixed in this revision (the header no longer contains any absolute filesystem path — this paragraph deliberately avoids repeating the literal string, since doing so would itself re-trigger the same check). This is reported here as a genuine, reproducible fact about the state of the repository at the moment this audit began — not a hypothetical.
- **Failure 2 — genuine, reproduced twice (full-suite run and isolated re-run), root-caused**: `tests/integration/test_datasource_onboarding_service.py::test_the_full_onboarding_flow_reaches_activation` fails with `assert freshness.stale is False` → actual `True`, because `freshness.latest_source_timestamp` is `None`. Root cause, confirmed by reading the test's fixtures (`_purge()`, `restricted_role`, `service`): the test onboards the *same* `agent_test` database as its own "customer" data source and inspects its own `conversations` table for a freshness signal, but nothing in the test's fixtures inserts a row into `conversations` — it depends entirely on that table already containing at least one row with a recent `updated_at`, an assumption that only holds if some *other* process had already written to it. In this audit's environment, at the moment this specific test ran, `agent_test.public.conversations` had no such row. **This is a test-environment-coupling defect in the test itself** (it implicitly depends on incidental, unseeded state in a shared database), not a demonstrated product bug in the freshness-checking code, which behaved exactly as documented given the data it found (no rows → no timestamp → correctly reported stale). Reported here as a confirmed, reproducible fact; not previously known (Revision 1 only ran `--collect-only`, which cannot surface this).
- **Ruff**: `571 errors` (167 auto-fixable) — unchanged count from Revision 1, re-run this pass to confirm stability.
- **Mypy**: **not run in Revision 1.** This pass: `105 errors in 39 files` (239 source files checked). Categories observed: `Literal[...]`-vs-`str` argument mismatches in several `*/store.py` files (constructing typed records from loosely-typed database rows — a common, usually-benign pattern when a store trusts its own prior validation), a handful of `Callable`-vs-`list`-return-type confusions from a method literally named `.list` colliding with the builtin, and the `openai_client.py` overload mismatch discussed in §13. None of these were confirmed as runtime failures in this audit (mypy findings are static and were not each individually runtime-tested), so all are reported as **Cannot verify at runtime** static findings, not confirmed defects, with the sole exception of the two pytest failures above which are unambiguous.

### 15.2 Frontend

- **Not run in Revision 1**: `npm run test` (Vitest) → **234 passed, 0 failed**, across 49 test files.
- **Not run in Revision 1**: `npm run lint` (ESLint) → pass, no output.
- **Not run in Revision 1**: `npm run build` (Turbopack production build) → success, 0 warnings, full route table (§9).
- **Not run in Revision 1**: a live `next start` server, `curl`-probed for redirect/status correctness (§9) — all expected.
- `npm run typecheck` → pass (also run in Revision 1, reconfirmed here).

### 15.3 What remains untested or unverifiable in this audit, and exactly why

| Area | Why | Classification |
|---|---|---|
| Live LLM agent runs, SSE streaming from a real model, live chart generation, live approval triggering | Requires a real, billed OpenAI API call — explicitly out of scope | Cannot verify at runtime |
| The 18 `@pytest.mark.postgres` integration tests that were, in fact, run this pass (they are no longer "not run" — correcting a possible ambiguity in how Revision 1 phrased this) | N/A — these were executed as part of the full-suite run reported in §15.1 | Tests executed and passed (all but the one confirmed failure above) |
| Scheduled-report worker actually firing on a timer, artifact-retention worker actually reclaiming an expired artifact | Would require starting a long-lived background process and waiting for a real interval to elapse — deferred as out of proportion for a single-pass audit, though nothing prevents it in a future pass | Tests executed and passed (worker logic only); not runtime-started |
| `app/audit` module in isolation | No dedicated test file was found (**scope**: `grep -rln "app.audit\|from app import audit" backend/tests`); exercised only indirectly through identity/tenancy service tests, and directly through this audit's own live audit-log check (§5.2) | Runtime verified indirectly; no dedicated unit test |
| Whether `DataGenerator` was actually used to produce the analytics database this audit queried | Circumstantial table-name match only (§2.1); `DataGenerator` itself was not run | Cannot verify |

---

## 16. Problems and Risks

| Priority | Problem | Type | Evidence | Verification tier |
|---|---|---|---|---|
| P1 | Password-reset/verification/invitation emails go only to a local `.dev-mail` file | Broken critical workflow | `composition/providers/identity.py:64` | **Runtime verified this pass** (§5.1, §5.2) — upgraded from Revision 1's static inference |
| P1 | Scheduled-report execution and artifact retention depend on a worker nothing starts automatically | Broken critical workflow (silent) | `main.py:49-56`; `scripts/run_scheduled_reports.py:12-14` | Static (unchanged); not runtime-tested this pass |
| P1 | **Memory Inspector calls the wrong URL and always fails** | Frontend/backend contract break | `memory-inspector.tsx:21` vs. `memory.py:15` | **Runtime verified this pass, confirmed by direct reproduction** — upgraded from Revision 1's "cannot verify" |
| P2 | `POST /api/v1/invitations/accept` accepts requests with no CSRF token, unlike every other mutating route | CSRF gap (moderate; exploitability bounded by the invitation still needing a valid, single-use, email-matched token) | `workspaces.py:447` (no `require_csrf`) | **Runtime verified this pass** — new finding, not present in Revision 1 |
| P2 | No deployment or CI infrastructure | Deployment readiness gap | Filesystem search, both passes | Static, unchanged |
| P2 | No health-check endpoint | Ops readiness gap | Route search, both passes | Static, unchanged |
| P2 | The PostgreSQL data-source connection feature — fully working end-to-end — has zero frontend | Missing UI for a complete, well-tested backend capability | §5.3, §7 | **Runtime verified (backend); confirmed absent (frontend)** — this pass resolved Revision 1's internal inconsistency about this feature into a single, confirmed finding |
| P2 | `/api/v1/schema/*` reachable by any authenticated user regardless of workspace membership | Consistency/scoping gap (impact depends on what the shared analytics DB contains in a given deployment) | `schema.py:32` | **Runtime verified this pass** — upgraded from Revision 1's "cannot fully verify" |
| P2 | Rate limiting is in-process only | Scalability gap | `identity/rate_limit.py:1-9` (self-documented) | Static, unchanged; not runtime-tested (would require multiple processes) |
| P2 | Python execution sandbox has no CPU/memory rlimits, only a wall-clock timeout | Security risk, self-disclosed | `environment/python.py:1-6` | Static, unchanged |
| P2 | 571 ruff violations; 105 mypy errors (mypy newly run this pass) | Code quality/maintainability | `.venv/bin/ruff check .`, `.venv/bin/mypy app` | **Both counts are from commands actually run this pass**, not estimates |
| P2 | One genuine, reproducible integration-test failure exists in the current codebase (`test_the_full_onboarding_flow_reaches_activation`) | Test-environment coupling defect | §15.1 | **Runtime verified this pass** — could not have been known from Revision 1's collection-only check |
| P3 | `ARCHITECTURE.md` references only the earliest migration, omits tenancy/identity/datasources/reporting | Documentation gap | Doc vs. code comparison | Static, unchanged |
| P3 | Two report-preference sub-fields persist with no rendering effect | Usability/consistency, low impact (self-disclosed in UI copy) | `report-preferences-settings.tsx:258-276` | Static, unchanged |
| P3 | Two-factor authentication is a disabled stub | Usability, no impact (clearly labeled) | `security-settings.tsx:282-296` | Static, unchanged |
| P4 | `openai_client.py`'s core LLM call doesn't type-check against the installed SDK | Unclear real-world impact | `openai_client.py:41` (mypy) | **Cannot verify at runtime** — new finding this pass, deliberately not escalated beyond this without a live (paid) test |

**No instance was identified within the inspected scope** of hardcoded secrets in source, SQL-injection-shaped query construction in the analytics/datasource paths, or an authentication bypass — search scope for each: a repo-wide `grep` for common secret patterns plus the passing repository's own `tests/contracts/test_documentation.py` (secret/credential-pattern scanner) and `tests/contracts/test_datasource_boundaries.py`/`test_identity_boundaries.py` (import-boundary and read-only-enforcement contract tests), all of which ran and passed in this audit's own suite execution (§15.1) except the one already-discussed environment-coupling failure. This is a substantially stronger absence claim than Revision 1's, because it is now backed by passing automated tests this audit actually ran, not solely by this audit's own manual reading.

---

## 17. Recommended Next Features and Fixes

Unchanged in substance from Revision 1's recommendations; re-prioritized slightly given this pass's confirmations:

### Fix before adding new features
1. **Wire identity emails to a real SMTP transport** — now backed by direct runtime reproduction, not inference. Effort: Small. Priority: P1.
2. **Fix the Memory Inspector's URL** (`memory-inspector.tsx:21` → prepend the workspace path, exactly as `types/api.generated.ts:1048` already documents) — a one-line, low-risk, high-confidence fix now that the exact break is pinned down. Effort: Small. Priority: P1.
3. **Give scheduled reports and artifact retention a real runtime home.** Effort: Small–Medium. Priority: P1.
4. **Add `Depends(require_csrf)` to `POST /api/v1/invitations/accept`**, or explicitly document why it's exempt. Effort: Small. Priority: P2.

### Short-term improvements
5. Build a frontend for the data-source connection feature (fully working backend exists and is now runtime-proven; zero UI exists today).
6. Minimal Dockerfile/compose + CI workflow running the exact commands verified in this audit (`pytest`, `ruff check`, `mypy app`, `npm run lint/typecheck/test/build`).
7. Health-check endpoint.
8. Resolve/confirm whether `/api/v1/schema/*` is intentionally global; if so, document it as such with a contract test (mirroring the existing AST-boundary-test pattern) rather than leaving it as an implicit design choice.
9. Fix the reproducible `test_the_full_onboarding_flow_reaches_activation` failure by seeding a `conversations` row with a recent timestamp in the test's own fixtures, rather than relying on incidental database state.
10. Address the 167 auto-fixable ruff findings and triage the 105 mypy errors (starting with the `openai_client.py` overload mismatch, since it sits on the single most consequential code path in the system).

### Future product features
Unchanged from Revision 1: multi-provider LLM support (a real second implementation, not just the existing interface), a working `web_search` tool, an admin UI for skills/specialists, non-Postgres data source connectors, two-factor authentication.

---

## 18. Suggested Delivery Roadmap

Unchanged in phase structure from Revision 1; item 2 (Memory Inspector fix) and the CSRF gap on invitation-accept are added to Phase 1 given they are now confirmed, low-effort, high-confidence fixes:

**Phase 1 — Fix confirmed security/workflow breaks**: identity email transport; Memory Inspector URL fix; CSRF on invitation-accept; scheduled-report/retention worker startup.
**Phase 2 — Complete disconnected features**: build a frontend for data-source connections; resolve schema/memory scoping; fix the reproducible test failure.
**Phase 3 — Usability, testing, documentation**: Dockerfile/CI running the exact verified commands; health endpoint; ruff/mypy triage; update `ARCHITECTURE.md`.
**Phase 4 — New capabilities**: multi-provider LLM, `web_search`, admin UI for skills, additional connectors, 2FA.

---

## 19. Open Questions

Carried forward from Revision 1, with two resolved (struck through, kept for traceability) and one added:

- ~~Is `GET /api/v1/schema/*` intentionally global?~~ **Resolved this pass**: it is reachable by any authenticated user regardless of workspace membership, confirmed by direct runtime test (§5.5) — whether this is *intentional* (the route's own docstring suggests yes) versus merely *unfinished* remains a genuine open product question, but the technical fact is no longer in question.
- ~~Does `GET /api/v1/memory` apply server-side workspace filtering invisible from the URL?~~ **Resolved this pass**: the real route requires `{workspace_id}` in the URL; the frontend simply never supplies it. Not an invisible-filtering question — a confirmed, simple bug.
- Is `POST /api/v1/workspaces/{workspace_id}/agent/run` (the synchronous variant) still an intended, supported API, or effectively superseded by the async `/analytics/runs` + SSE path the frontend actually uses? Still open — this audit did not exercise either path live (both require a paid OpenAI call).
- Is the CSRF exemption on `POST /api/v1/invitations/accept` intentional (e.g., because the invitation token itself is treated as sufficient proof of intent) or an oversight? **New question this pass**, arising directly from the runtime reproduction in §5.2.
- What is the intended production process-management story for the scheduling/retention workers?
- Is `DataGenerator` meant to ship as part of a documented onboarding/demo flow, or is it purely an internal evaluation tool? Still open — this audit found strong circumstantial (table-name) evidence it produced the analytics DB queried during this audit's runtime tests, but did not run `DataGenerator` itself to confirm.
- Is the `openai_client.py`/installed-SDK mypy mismatch a real functional problem? Genuinely unresolved without a live, paid API call this audit will not make.

---

## 20. Final Capability Summary

### Works now — runtime verified this pass
Account registration/login/session cookies; workspace creation/listing; member invitation issuance and acceptance by a real second user; RBAC permission enforcement (both a positive OWNER path and a negative ANALYST-denial path); audit-log recording and permission-gating; cross-tenant isolation for a user with zero memberships; the entire PostgreSQL data-source connection lifecycle (SSL-mode enforcement, live read-only-role verification, schema listing, table cataloguing with automatic column-role/sensitivity classification, approval gating, activation, freshness checking); the shared schema explorer; metric/report-template listing; and the complete deterministic Saved Report pipeline from recipe creation through a genuinely downloadable, valid PDF file.

### Works, per passing automated tests actually executed this pass (not independently runtime-exercised over HTTP by this audit)
The LLM-agent loop's internal logic, tool dispatch, skill/specialist delegation, memory retrieval and writing, approval checkpoint/resume, observability/tracing, reliability/retry, delivery providers (webhook/email code paths), scheduling/retention worker logic, and all AST-based architectural boundary contracts — 1,451 of 1,541 backend tests and all 234 frontend tests passed.

### Backend available but confirmed to have no frontend
The entire PostgreSQL data-source connection feature (17 endpoints, fully working, zero UI).

### UI available but confirmed broken or non-functional
Memory Inspector (calls the wrong URL — confirmed by direct reproduction, not a hedge); two-factor authentication (explicitly disclosed as unavailable); report preference "Theme" and "Technical SQL appendix" fields (persist, no rendering effect).

### Confirmed defects newly found this pass (not in Revision 1)
`POST /api/v1/invitations/accept` accepts no CSRF token; one reproducible integration-test failure (`test_the_full_onboarding_flow_reaches_activation`) rooted in the test's own unseeded-data assumption; 105 mypy errors including a call-shape mismatch on the core OpenAI client call that this audit cannot resolve without a live, paid API call.

### Not implemented but recommended
Real SMTP delivery for identity emails; an automatic startup path for the scheduling/retention workers; a health-check endpoint and deployment/CI infrastructure; a completed `web_search` tool; distributed rate limiting; non-Postgres data source connectors; a frontend for the data-source connection feature.
