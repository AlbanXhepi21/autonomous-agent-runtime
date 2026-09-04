# Backend architecture

The backend is a single FastAPI application (`backend/app/main.py`) organized as ~25
top-level packages under `backend/app/`. This document maps what each package is for,
disambiguates three easily-confused package names, and describes how the object graph is
wired together. Feature-specific behavior (the agent loop, analytics, reporting, auth) is
covered in its own document — this one is about structure.

## Package map

| Package | Purpose (verified from code, not from its own docstring — see [Known inconsistencies](#known-inconsistencies)) |
|---|---|
| [`contracts/`](../../backend/app/contracts) | Typed schemas shared across packages (`AgentAction`, `AnswerSource`, `InvestigationPlan`, `AgentDefinition`) — a leaf package, see [Package boundaries](#package-boundaries) |
| [`core/`](../../backend/app/core) | Domain exceptions, `RuntimeLimits`, logging/redaction helpers, shared validators — the other leaf package |
| [`runtime/`](../../backend/app/runtime) | The actual agent decision loop, planning/finish-gate logic, delegation, context building — see [agent-runtime.md](agent-runtime.md) |
| [`orchestration/`](../../backend/app/orchestration) | Run lifecycle *around* a runtime run (creation, SSE projection, reruns) and document publishing — not the loop itself, see [Disambiguating runtime, orchestration, and composition](#disambiguating-runtime-orchestration-and-composition) |
| [`composition/`](../../backend/app/composition) | Dependency-injection root — builds every concrete object the app runs on |
| [`tools/`](../../backend/app/tools) | Every registered agent tool and the executor that runs one safely |
| [`skills/`](../../backend/app/skills) | Discovery/loading of Markdown skill instructions |
| [`resources/`](../../backend/app/resources) | Static assets: specialist and skill definitions, report templates — not code |
| [`llm/`](../../backend/app/llm) | `LLMClient` interface and its one concrete implementation, `OpenAIClient` |
| [`security/`](../../backend/app/security) | Capability-based authorization, risk classification, human-approval gating, credential references |
| [`reliability/`](../../backend/app/reliability) | Retry policy and failure-category taxonomy for LLM/tool failures |
| [`environment/`](../../backend/app/environment) | Sandboxed filesystem, command, and Python execution primitives |
| [`observability/`](../../backend/app/observability) | Structured tracing (in-memory only today) and evidence/citation resolution |
| [`analytics/`](../../backend/app/analytics) | SQL validation/execution, schema discovery, semantic metrics, document/chart rendering — see [data-analysis.md](data-analysis.md) |
| [`datasources/`](../../backend/app/datasources) | Workspace-connected PostgreSQL data source onboarding, governance, encryption |
| [`reports/`](../../backend/app/reports) | Saved-report definitions, execution, and their store — see [reporting.md](reporting.md) |
| [`memory/`](../../backend/app/memory) | Agent memory (working/episodic/long-term), lexical retrieval |
| [`artifacts/`](../../backend/app/artifacts) | Durable file registration, retention/expiry |
| [`conversations/`](../../backend/app/conversations) | Conversation/message/run persistence |
| [`delivery/`](../../backend/app/delivery) | Link, webhook, and email delivery of published artifacts |
| [`scheduling/`](../../backend/app/scheduling) | Recurrence calculation and the scheduled-report worker |
| [`identity/`](../../backend/app/identity) | Users, sessions, password/email-verification tokens |
| [`tenancy/`](../../backend/app/tenancy) | Workspaces, memberships, roles, invitations |
| [`audit/`](../../backend/app/audit) | Append-only audit log of sensitive account/workspace actions |
| [`api/`](../../backend/app/api) | FastAPI routers and per-request dependencies |
| [`db/`](../../backend/app/db) | SQLAlchemy models (`records.py`) and the async session factory |

## Disambiguating `runtime`, `orchestration`, and `composition`

These three names are the most likely source of confusion for a new contributor, and the
audit that preceded this document confirmed the confusion is warranted — their names
alone don't make the split obvious:

- **`runtime/`** is the agent itself: `AgentRunner.run()` is the one-next-action loop that
  calls the model, dispatches actions, and enforces every iteration/tool/error limit. If
  you are changing *how the agent decides or acts*, this is the package. See
  [agent-runtime.md](agent-runtime.md).
- **`orchestration/`** sits one layer above a runtime run and never itself decides what
  the agent does next. `AgentRunManager` (`orchestration/run_manager.py`) spawns a runtime
  run as a task, persists it, and projects its internal trace events into the public SSE
  event shape the frontend consumes. `ReportPublisher` (`orchestration/publishing.py`) and
  `ReportRerunService` (`orchestration/reruns.py`) turn an already-completed run into a
  document or recompute its figures — both are explicitly non-LLM (see
  [reporting.md](reporting.md)). If you are changing *how a run's lifecycle or output is
  managed after the fact*, this is the package.
- **`composition/`** composes the **object graph**, not prompts or agent pipelines,
  despite a name that could suggest either. It is the dependency-injection root: one file
  per subsystem under `composition/providers/`, each exposing `get_x()` factory functions
  decorated with `@provider` (`composition/lifecycle.py`), which caches each provider's
  result as a process-scoped singleton and registers it for teardown on `shutdown()`. If
  you are changing *which concrete implementation is wired to an interface* (e.g. swapping
  an in-memory store for a Postgres one), this is the package —
  `composition/providers/tools.py::get_tool_registry()` is a representative example: it is
  the single place every `Tool` is imperatively registered.

## Package boundaries

`backend/tests/contracts/test_package_boundaries.py` enforces two structural rules by
parsing the AST of every file under `backend/app/`, not by convention:

1. **No import cycle between any two top-level packages.**
2. **`contracts` and `core` are leaf packages** — they may import each other but nothing
   else, so any other package can depend on them without risk of a cycle. This is what
   lets `llm`, `security`, and `memory` each describe the shape of what they consume
   (a tool's arguments, an action, an answer) without importing the runtime that
   constructs those objects.

### Known inconsistencies

- **Package docstrings for `runtime/`, `tools/`, and `skills/` are stale.** Their
  `__init__.py` files currently read "Agent package for future autonomous execution
  components," "Tools package for future agent capabilities," and "Skills package for
  future specialized instructions," respectively — leftover placeholder text from before
  these packages were built out. All three are fully implemented today (see
  [agent-runtime.md](agent-runtime.md)); do not take these docstrings as a statement of
  current scope.
- **A package-boundary test still names a package that no longer exists.**
  `test_provider_and_storage_packages_do_not_import_the_runtime` checks whether `llm`,
  `security`, or `memory` import `app.agent` — but there is no `app/agent/` package in
  the current tree (the runtime package was renamed to `app/runtime/` at some point in the
  project's history, visible in `ARCHITECTURE.md`'s own stale references to `app/agent/`).
  The test currently cannot fail, because the module name it's guarding against is
  unreachable; it does not check for an import of `app.runtime`, which is the package the
  rule is presumably meant to guard against today.

## HTTP layer

`backend/app/main.py::create_app()` builds one `FastAPI` instance, adds CORS middleware
scoped to `ANALYTICS_UI_FRONTEND_ORIGINS` (GET/POST/PATCH/DELETE only, credentials
allowed), and includes 17 routers from `backend/app/api/routes/` — see
[authentication-and-tenancy.md](authentication-and-tenancy.md) for which routes require a
`workspace_id`-scoped `TenantContext` and which don't. There is no API versioning scheme
beyond the `/api/v1/` prefix baked into each router; `create_app()` does not set a custom
`version=`, `docs_url=`, or `openapi_url=`, so FastAPI's defaults apply (`/docs`,
`/openapi.json`, schema version `"0.1.0"`).

Per-request cross-cutting concerns (session resolution, CSRF, tenant context, permission
checks) live in `backend/app/api/dependencies.py` as FastAPI dependencies rather than
middleware — see [authentication-and-tenancy.md](authentication-and-tenancy.md) for the
exact resolution chain.
