# Repository structure

A quick-lookup map of where things live. For narrative explanation of why the backend is
organized this way, see [architecture/backend.md](../architecture/backend.md).

```text
autonomous-agent/
├── README.md                   Primary project reference (setup, capability overview)
├── ARCHITECTURE.md              Stale — pre-restructure snapshot, not current (see limitations.md)
├── docs/                        This documentation set
│   ├── README.md                 Documentation landing page
│   ├── getting-started/          Setup, configuration, troubleshooting
│   ├── architecture/              System-level design docs (backend, frontend, runtime, security, ...)
│   ├── concepts/                  Feature-level explanations (tools, evidence, charts, metrics, ...)
│   ├── reference/                 This directory — structure, env vars, commands, permissions, limitations
│   ├── TENANCY.md, DATASOURCES.md, METRICS.md   Pre-existing, current, accurate reference docs
│   └── UI1_WORKBENCH_API.md, V7_FINAL_REPORT.md  Historical snapshots
├── backend/
│   ├── app/                      The FastAPI application — see the package table below
│   ├── migrations/versions/       26 linear Alembic migrations
│   ├── evals/                     Deterministic evaluation harness (not wired into CI)
│   ├── scripts/                   Operational scripts — see commands.md
│   ├── tests/                     api/ contracts/ fixtures/ integration/ unit/
│   ├── pyproject.toml             The only backend dependency manifest (no requirements.txt)
│   └── .env.example               Backend environment template
└── frontend/
    ├── src/app/                   Next.js App Router pages
    ├── src/features/              Domain feature modules (auth, settings, tenancy, workbench)
    ├── src/components/ui/         Shared UI primitives
    ├── src/lib/                   API client, auth/tenancy helpers, appearance
    ├── src/types/                 Hand-written aliases over the generated OpenAPI types
    ├── test/setup.ts               Vitest setup (tests are colocated under src/)
    ├── package.json                npm scripts — see commands.md
    └── .env.local.example          Frontend environment template (see troubleshooting.md — not tracked in git)
```

## Backend package table

| Package | What lives here |
|---|---|
| `app/contracts/` | Shared typed schemas (leaf package) |
| `app/core/` | Exceptions, `RuntimeLimits`, logging/redaction (leaf package) |
| `app/runtime/` | The agent decision loop |
| `app/orchestration/` | Run lifecycle and document publishing around a run |
| `app/composition/` | Dependency-injection root — every `get_x()` provider |
| `app/tools/` | Every registered tool and its executor |
| `app/skills/` | Skill discovery/loading |
| `app/resources/` | Static assets: specialists, skills, report templates |
| `app/llm/` | `LLMClient` interface + `OpenAIClient` |
| `app/security/` | Capability authorization, risk classification, approval gating |
| `app/reliability/` | Retry policy, failure taxonomy |
| `app/environment/` | Sandboxed filesystem/command/Python execution |
| `app/observability/` | Tracing (in-memory only) and evidence/citation resolution |
| `app/analytics/` | SQL validation/execution, schema discovery, semantic metrics, document/chart rendering |
| `app/datasources/` | Workspace-connected PostgreSQL onboarding and governance |
| `app/reports/` | Saved-report definitions, execution, store |
| `app/memory/` | Agent memory |
| `app/artifacts/` | Durable file registration and retention |
| `app/conversations/` | Conversation/message/run persistence |
| `app/delivery/` | Link/webhook/email delivery |
| `app/scheduling/` | Recurrence calculation and the scheduled-report worker |
| `app/identity/` | Users, sessions, tokens |
| `app/tenancy/` | Workspaces, memberships, roles, invitations |
| `app/audit/` | Append-only audit log |
| `app/api/` | FastAPI routers and dependencies |
| `app/db/` | SQLAlchemy models and session factory |

Full package-by-package explanation, including the `runtime`/`orchestration`/`composition`
disambiguation and known docstring inconsistencies, is in
[architecture/backend.md](../architecture/backend.md).

## Where to find specific things

| Looking for... | Location |
|---|---|
| A tool's implementation | `backend/app/tools/` (database tools under `tools/database/`) |
| A skill's instructions | `backend/app/resources/skills/<name>/SKILL.md` |
| A specialist's definition | `backend/app/resources/specialists/<name>/AGENT.md` + `metadata.json` |
| A report template | `backend/app/resources/report_templates/<name>/metadata.json` + `theme.json` |
| The metric registry | `backend/app/analytics/semantics/metrics.py` |
| A database migration | `backend/migrations/versions/` |
| An API route | `backend/app/api/routes/` |
| The frontend's chart renderer | `frontend/src/features/workbench/components/chart-renderer.tsx` |
| Generated frontend API types | `frontend/src/types/api.generated.ts` (do not hand-edit) |
