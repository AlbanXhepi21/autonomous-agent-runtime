# Tenant Isolation

This document classifies every persisted resource by ownership and records the
migration that gave it a real, backend-enforced tenant boundary. It covers the
resources named in the tenant-isolation migration: conversations, messages,
agent runs, run traces, working/episodic/long-term memory, artifacts, report
definitions, report executions, schedules, data sources, semantic
configurations, and evaluation records.

## Classification

### Global system resources

Shared by every tenant; never carry a `workspace_id`.

| Resource | Where it lives | Why it's global |
|---|---|---|
| Users | `users` table | Identity is global; a `workspace_memberships` row is the tenant-scoping join, not the user record itself. |
| Workspaces | `workspaces` table | The tenant boundary itself has no further tenant to belong to. |
| Report templates | `app/resources/**/metadata.json`, `theme.json` | Content, not code or data — a document shape, versioned on disk, shared by every workspace that publishes into it. |
| Metric / semantic definitions | `app/analytics/semantics/metrics.py` (`MetricRegistry`) | "Runtime-owned, versioned business metric definitions (not database content)" per its own docstring — declared in code/JSON, never written by a tenant. |
| Analytics schema policy / allowlist | `app/analytics/schema/allowlist.py` | Governs the legacy, single, process-wide `ANALYTICS_DATABASE_URL` demo database — a pre-tenancy resource, out of scope for this migration (see Known Limitations). |
| Skills / specialist definitions | `app/resources/{skills,specialists}/**` | On-disk instructions shared by every tenant's agent runs. |
| Evaluation datasets and runs | top-level `evals/` package, `scripts/run_agent_scenarios.py` | Developer/CI tooling invoked from the command line, never through a tenant-facing route. Nothing here is persisted to a database table — no `EvaluationRecord` exists. Reports are ephemeral process output. |

### Tenant-owned resources (direct)

Carry their own `workspace_id` column, the root of an ownership tree.

| Resource | Table | Notes |
|---|---|---|
| Conversations | `conversations` | Root of the conversation → message → run tree. |
| Artifacts | `artifacts` | Correlated by `run_id` string, not a foreign key (the artifact backend is switchable) — needs its own column. |
| Memories (working/episodic/long-term) | `memories` | Discriminated by `memory_type`; keyed loosely by `run_id`/`session_id` strings with no reliable FK parent — needs its own column. |
| Deliveries | `deliveries` | `artifact_id` deliberately carries no foreign key (same switchable-backend reasoning as artifacts) — needs its own column, populated from the artifact's workspace at delivery-creation time. |
| Data sources | `data_sources` | Already had a `workspace_id` *string* column (an unenforced convention); this migration converts it to a real foreign key. |
| Saved report definitions | `saved_reports` | Same string → foreign key conversion as data sources. |
| Scheduled reports | `scheduled_reports` | Same string → foreign key conversion. |

### Tenant-owned resources (child — verified through their parent)

No new column. Ownership is checked by joining to (or first loading) the
parent, per "all child-resource lookups must verify tenant ownership through
their parent."

| Resource | Table | Parent | How ownership is checked |
|---|---|---|---|
| Messages | `messages` | `conversations` (via `conversation_id`, `NOT NULL`) | `ConversationStore` methods join to `conversations.workspace_id`. |
| Agent runs | `agent_runs` | `conversations` (via `conversation_id`, `NOT NULL`) | Same join; `get_run(workspace_id, run_id)` is the one method that needs it explicitly, since a bare `run_id` has no workspace of its own. |
| Data source tables/columns/relationships | `data_source_tables`, `data_source_columns`, `data_source_relationships` | `data_sources` (via `data_source_id`) | Unchanged — `DataSourceStore` already re-checks `record.workspace_id != workspace_id` after every ID lookup; this pattern predates this migration and is the model the rest of the codebase now follows. |
| Saved report executions | `saved_report_executions` | `saved_reports` (via `saved_report_id`) | `SavedReportStore` loads the parent definition first; `finish_execution` — previously looked up by bare `run_id` — now takes `workspace_id` too (see Known Gaps Closed). |
| Run traces | in-memory `TraceStore`, keyed by `run_id` | `agent_runs` → `conversations` | Not a database table — process-local and non-persistent by design (V7.1). The **route** (`GET /runs/{run_id}/trace`) resolves the owning conversation through `ConversationStore.get_run(workspace_id, run_id)` before it will ask the trace store for anything. |
| Approvals | file-backed `ApprovalStore`, keyed by `run_id` | `agent_runs` → `conversations` | Same pattern as traces: the route verifies run ownership before touching the approval store, rather than teaching the file store a new persistence model. |

### User-owned resource within a tenant

`SavedReportRecord.owner` is the one field in this codebase that already
gestures at per-user (not just per-workspace) ownership — a nullable string
recorded at creation time, informational today. No route currently restricts
a saved report to its owner *within* a workspace (any member with
`MANAGE_MEMBERS`-independent read access can see every saved report in the
workspace); building that finer-grained ACL is future work, not part of this
migration. It is called out here so the classification is honest about what
exists versus what is enforced.

## Migration sequence

Continuing from `20260902_0015` (workspace invitations), each step is its own
revision so the safety story is auditable one operation at a time:

| Revision | Step | What it does |
|---|---|---|
| `20260903_0016` | 1. Identify a default tenant | Creates one `workspaces` row, slug `legacy`, name "Legacy (Pre-Tenancy Data)". Every row with no reliable ownership signal lands here — see "Backfill mapping" below. |
| `20260903_0017` | — | Adds nullable `workspace_id` (UUID) to `conversations`, `artifacts`, `memories`, `deliveries`; adds a parallel nullable `workspace_id_new` (UUID) to `data_sources`, `saved_reports`, `scheduled_reports` alongside their existing string column. |
| `20260903_0018` | 2. Backfill existing records | Data-only migration; see mapping rules below. |
| `20260903_0019` | 3. Validate the backfill | Runs a `COUNT(*) WHERE workspace_id IS NULL` (or `workspace_id_new IS NULL`) against all seven tables and **raises**, aborting the migration chain, if any row was missed. A real gate, not a comment. |
| `20260903_0020` | 4. Add non-null constraints | Drops the old string `workspace_id` on the three converted tables, renames `workspace_id_new` → `workspace_id`, then sets `NOT NULL` on all seven `workspace_id` columns. |
| `20260903_0021` | 5. Add foreign keys | `workspace_id → workspaces.id ON DELETE RESTRICT` on all seven tables — matching this codebase's existing convention that durable history is never silently cascaded away. |
| `20260903_0022` | 6. Add tenant-scoped indexes | New composite indexes on the four newly-scoped tables; recreates the three data-source/report/schedule indexes that were dropped along with their old string column. |

### Backfill mapping (step 2)

For `conversations`, `artifacts`, `memories`, `deliveries` — these tables had
**no** tenant concept at all before this migration, so every existing row is
assigned to the `legacy` workspace created in step 1. There is no signal in
the data to do anything more specific, and guessing would be exactly the
"silently assign ambiguous production data to the wrong user" this migration
is required not to do.

For `data_sources`, `saved_reports`, `scheduled_reports` — these tables
already carried a caller-supplied `workspace_id` *string*, unauthenticated but
not meaningless: every route that wrote one filtered its own reads by the
same string. The migration preserves that grouping rather than collapsing it:

- Every distinct string value across all three tables is enumerated.
- The literal value `"default"` (the `DEFAULT_WORKSPACE_ID` every route
  actually used) maps to the same `legacy` workspace from step 1.
- Every other distinct string gets its own new `workspaces` row, named
  `Legacy: <original string>`, so whatever nominal separation existed in the
  data is preserved rather than merged.

**Operational note:** because tenant isolation is now strictly enforced,
none of this backfilled data is visible to anyone until a human operator
creates a membership in the relevant legacy workspace. This is deliberate —
see the Known Limitations note in the top-level implementation report.

## Known unsafe-lookup gaps closed

Two store methods identified in the earlier architecture audit retrieved a
tenant-owned record by a bare, unscoped ID and are fixed by this migration:

- `SavedReportStore.finish_execution` — previously looked up by `run_id`
  alone; now also takes `workspace_id` and verifies it through the parent
  saved report before writing.
- `ScheduledReportStore.record_run_result` — previously looked up by
  `scheduled_report_id` alone; same fix, verified through the schedule's own
  `workspace_id`.

`ArtifactStore.claim_expired` and `ScheduledReportStore.claim_due` remain
intentionally cross-tenant: both are background-worker sweeps that must see
every tenant's due/expired rows to do their job, not a caller-facing lookup.

## Isolation test coverage

Two dedicated cross-tenant test suites, alongside the workspace-scoping tests
already embedded in each resource's own unit/API/integration test file:

- `tests/integration/test_tenant_isolation.py` — repository-level, against a
  real PostgreSQL database with two minted `workspaces` rows (Tenant A,
  Tenant B). Proves direct UUID substitution against `ConversationStore`,
  `MemoryStore`, `ArtifactStore`, and `DeliveryStore` methods: a real
  identifier from Tenant B, handed to Tenant A's own store, resolves to
  nothing (never a 403, never a partial read) exactly like a fabricated ID
  would.
- `tests/api/test_tenant_isolation.py` — HTTP-level, two `TestClient` apps
  sharing one backing store/fake per resource, each pinned to a different
  synthetic tenant via `tests.support.override_tenant_context`. Proves the
  same UUID-substitution attack against the actual route functions for
  conversations, messages, runs, the SSE event stream, event history, run
  traces, and artifacts (including download).
- Data sources, saved reports, and scheduled reports carry their own
  cross-workspace proofs directly in `tests/api/test_datasources_api.py` /
  `test_saved_reports_api.py` / `test_scheduled_reports_api.py` (HTTP) and
  `tests/integration/test_datasource_store.py` /
  `test_saved_report_store.py` / `test_scheduled_report_store.py`
  (repository), rather than being duplicated into the two files above.

`tests/support.override_tenant_context(app, *, workspace_id=None,
role=Role.OWNER)` is the shared helper: it overrides `get_tenant_context`
and `require_csrf` on a given FastAPI app to resolve every tenant-scoped
route to one fixed, fully-permissioned synthetic tenant, bypassing real
cookie auth — that mechanism is already proven end to end by
`test_auth_api.py` and `test_workspaces_api.py`, so business-route tests
only need a stable, known tenant to assert against.

### Production bugs this migration's tests surfaced

Fixing the pre-existing test suite against the new `workspace_id`-first
signatures surfaced two real defects, both fixed alongside the test that
exposed them:

- `app/tools/database/analyze.py` (`AnalyzeDatasetTool.execute_for_run`) —
  never threaded `workspace_id` through to `ArtifactStore.register` when
  registering a chart it generated, so every `analyze_dataset` run that
  produced a chart would have failed outright once the artifact store
  required `workspace_id`. Now validates and threads it exactly like
  `RegisterArtifactTool` and `GenerateReportTool` already did.
- `app/reports/store.py` (`PostgresSavedReportStore.create_execution`) —
  called `session.get()` (which implicitly begins a transaction) and then
  opened a second explicit `session.begin()`, which SQLAlchemy always
  rejected with `InvalidRequestError: A transaction is already begun on this
  Session`. This meant **every saved-report execution — manual preview/
  publish via the API, and every scheduled run** — was broken against real
  PostgreSQL. Fixed by moving the parent lookup inside the `session.begin()`
  block, matching the pattern already used by `update`, `finish_execution`,
  and `record_run_result` in the same file.

## Known limitations

- **The legacy analytics database (`ANALYTICS_DATABASE_URL`) remains
  global**, as flagged in the original architecture audit — it predates the
  workspace-scoped `data_sources` model and this migration does not resolve
  that tension.
- **No reactivation flow for removed memberships** (unchanged from the
  tenancy-model phase) — this migration does not add one.
- **Legacy backfilled data requires manual membership provisioning** before
  it becomes reachable again, by design (see above).
