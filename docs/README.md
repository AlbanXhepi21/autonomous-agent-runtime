# autonomous-agent documentation

`autonomous-agent` pairs a bounded-autonomy agent runtime with a Next.js "Data Analyst
Workbench": it investigates a Postgres analytics database, cites the queries behind every
figure it reports, and can publish the result as a PDF or Word document. The backend also
implements its own authentication, multi-tenant workspaces, scheduled reports, and
delivery (link/webhook/email) — this documentation set is being built up to cover all of
it, starting with getting a local environment running.

## Who this is for

- **New contributors** getting a backend + frontend environment running for the first time.
- **Backend contributors** working on the agent runtime, analytics engine, or persistence layers.
- **Frontend contributors** working on the Next.js Workbench.
- **Reviewers and operators** who need to understand what is implemented, what is partial, and what is not yet built.

## Current documentation

### Getting started

| Document | Covers |
|---|---|
| [Prerequisites](getting-started/prerequisites.md) | Verified language/runtime/database versions and optional tooling |
| [Local development](getting-started/local-development.md) | Exact, verified setup sequence from clone to first analysis |
| [Configuration](getting-started/configuration.md) | Every environment variable, its purpose, and its sensitivity |
| [Troubleshooting](getting-started/troubleshooting.md) | Verified fixes for the setup problems a new environment is most likely to hit |

### Architecture

| Document | Covers |
|---|---|
| [Overview](architecture/overview.md) | Product purpose, system components, request lifecycle, package boundaries, and three Mermaid diagrams |
| [Backend](architecture/backend.md) | The backend package map, and disambiguation of `runtime`/`orchestration`/`composition` |
| [Frontend](architecture/frontend.md) | Next.js route structure, the Workbench feature module, the OpenAPI codegen pipeline |
| [Agent runtime](architecture/agent-runtime.md) | The decision loop, action types, limits, duplicate detection, delegation, finish gating, investigation planning, and approval checkpoints — with each mechanism labeled runtime-enforced, model-instructed, or human-approval |
| [Data analysis](architecture/data-analysis.md) | Schema discovery, read-only enforcement, sqlglot AST validation, allowlisting, limits, and semantic metric execution |
| [Reporting](architecture/reporting.md) | The compiled-report model, block kinds, templates/themes, PDF/DOCX generation, evidence appendix, narrative freshness, reruns, and the artifact lifecycle |
| [Persistence](architecture/persistence.md) | What's actually stored per domain, with an entity-relationship diagram |
| [Authentication and tenancy](architecture/authentication-and-tenancy.md) | Session/CSRF mechanics, the workspace/role model, permission resolution, and cross-tenant isolation |
| [Security boundaries](architecture/security-boundaries.md) | Trust boundaries around input, model output, tool arguments, SQL, filesystem, external content, credentials, and report publishing |

### Concepts

Feature-level explanations, each built by inspecting the live registries and contracts
rather than restating the architecture docs:

| Document | Covers |
|---|---|
| [Tools, skills, and specialists](concepts/tools-skills-and-specialists.md) | A full inventory — every tool's capability/risk/approval behavior, every skill and specialist, and exactly why `web_search` is unreachable |
| [Conversations and runs](concepts/conversations-and-runs.md) | Conversation vs. run, run states, messages vs. observations, trace events, compaction |
| [Memory](concepts/memory.md) | The three memory types, lexical (non-vector) retrieval, and why there's no compaction |
| [Evidence and citations](concepts/evidence-and-citations.md) | `query_###` generation, rerun evidence, the trace ledger, citation resolution, and precisely what a citation does and does not prove |
| [Charts and displays](concepts/charts-and-displays.md) | Every chart type, the `ChartSpec` contract with a valid example, dataset references, and the two independent renderers |
| [Semantic metrics](concepts/semantic-metrics.md) | An index over all 28 metrics — status, executability, grain, dimensions, filters — cross-linked to the machine-generated `METRICS.md` |
| [Report templates](concepts/report-templates.md) | Every template's sections, required/optional content slots, formats, and theme |
| [Artifacts](concepts/artifacts.md) | Creation, lifecycle states, storage backends, retention, and size limits |

### Reference

Flat lookup material — structure, exact commands, exact variables, exact permissions, and
an honest limitations list:

| Document | Covers |
|---|---|
| [Repository structure](reference/repository-structure.md) | Where things live, and a package-purpose table |
| [Environment variables](reference/environment-variables.md) | Every variable, its default, and whether it's required/sensitive, at a glance |
| [Commands](reference/commands.md) | Every development, test, migration, codegen, preview, and operational command |
| [Permissions](reference/permissions.md) | The tenant role-permission matrix, derived from the centralized mapping |
| [Limitations](reference/limitations.md) | The consolidated, code-verified limitations list — including one not documented anywhere else in this repository |

### Guides

Step-by-step instructions for a specific task, each referencing real contracts and
verified commands:

| Document | Covers |
|---|---|
| [Running an analysis](guides/running-an-analysis.md) | The full user + developer flow: start, stream, evidence, displays, preview, publish, download, reruns, narrative freshness |
| [Adding a tool](guides/adding-a-tool.md) | The `Tool` ABC, registration, capability mapping, and the specialist-only failure mode of skipping it |
| [Adding a skill](guides/adding-a-skill.md) | `SkillMetadata`, filesystem discovery, and the two required files |
| [Adding a specialist](guides/adding-a-specialist.md) | `AgentMetadata`/`AgentDefinition`, discovery-time validation of `allowed_tools`/`allowed_skills` |
| [Adding a semantic metric](guides/adding-a-semantic-metric.md) | `MetricDefinition`, the two-tier test requirement, and the `docs/METRICS.md` regeneration contract |
| [Adding a chart type](guides/adding-a-chart-type.md) | Every backend and frontend file a new `ChartType` value touches — a closed enum, not a plugin system |
| [Adding a report template](guides/adding-a-report-template.md) | `ReportTemplate`/`ReportTheme`, filesystem discovery, and the structure/theme separation test |
| [Generating reports outside a live run](guides/generating-reports.md) | Saved reports, scheduled reports, and the non-agent rerun pipeline |
| [Database migrations](guides/database-migrations.md) | Naming convention, the multi-step risky-change pattern, and testing a migration |
| [Testing](guides/testing.md) | Every test tier, targeted-run examples, and which tiers need a real database |

### API

HTTP contract reference — not a reproduction of the OpenAPI schema:

| Document | Covers |
|---|---|
| [Overview](api/overview.md) | Base path, auth, tenant context, error format (which isn't fully uniform), pagination (which doesn't exist everywhere), OpenAPI location |
| [Authentication](api/authentication.md) | Register/login/logout/reset/verify, exact cookies and CSRF behavior |
| [Analytics](api/analytics.md) | The Workbench's actual run/report lifecycle endpoints |
| [Reports and artifacts](api/reports-and-artifacts.md) | Saved/scheduled report CRUD and execution, artifact download/list/preview |
| [Streaming events](api/streaming-events.md) | The complete 24-type SSE vocabulary, wire format, and reconnection limits |

### Operations

Only what's actually supported — no Docker, Kubernetes, Redis, or cloud object storage
exist in this repository, and these documents say so explicitly rather than assuming them:

| Document | Covers |
|---|---|
| [Deployment](operations/deployment.md) | Required services, processes to run, production configuration, rollback, health checks |
| [Database](operations/database.md) | The two-database split, migrations, connection requirements |
| [Observability](operations/observability.md) | What logging/metrics/tracing exist in-process, and what doesn't exist at all |
| [Security](operations/security.md) | Operational guidance layered on the architecture's trust boundaries |
| [Backups and retention](operations/backups-and-retention.md) | What's implemented (artifact retention) vs. what isn't (backups) |
| [Production readiness checklist](operations/production-checklist.md) | Everything to verify or consciously accept before a real deployment |

### Contributing

| Document | Covers |
|---|---|
| [Development workflow](contributing/development-workflow.md) | Observed branch/commit conventions, package boundaries, test expectations |
| [Coding conventions](contributing/coding-conventions.md) | Ruff/mypy/eslint config, the observed docstring pattern, contract-schema conventions |
| [Pull requests](contributing/pull-requests.md) | The manual checklist that stands in for this repository's absent CI |
| [Documentation guidelines](contributing/documentation-guidelines.md) | How this `docs/` tree is organized, and what to update for a given kind of change |

### Existing reference material

These were written and verified before this documentation set and remain current:

- [`TENANCY.md`](TENANCY.md) — workspace/membership model and tenant isolation
- [`DATASOURCES.md`](DATASOURCES.md) — workspace-connected PostgreSQL data source onboarding
- [`METRICS.md`](METRICS.md) — the semantic metric registry (machine-generated, do not hand-edit)

`UI1_WORKBENCH_API.md` and `V7_FINAL_REPORT.md` also exist but predate the current
tenancy model and are point-in-time snapshots rather than living documentation; treat them
as historical until a later documentation phase reconciles or archives them.

## Reading paths

Every document below is linked from a section above — these are just a suggested order
for a given goal. Pick the path closest to what you're trying to do; nothing stops you
from jumping straight to a page you already know you need.

### New users

Setting up this project for the first time:

1. [Prerequisites](getting-started/prerequisites.md)
2. [Local development](getting-started/local-development.md)
3. [Configuration](getting-started/configuration.md) — as a reference while editing `.env` files
4. [Troubleshooting](getting-started/troubleshooting.md) — if any step fails
5. [Architecture → Overview](architecture/overview.md) — once your environment runs, this is the map to everything else
6. [Limitations](reference/limitations.md) — the single most consequential finding in this documentation set

### Backend developers

Working in `backend/app/`:

1. [Architecture → Backend](architecture/backend.md) — the package map and the `runtime`/`orchestration`/`composition` disambiguation
2. [Architecture → Agent runtime](architecture/agent-runtime.md) — the decision loop every feature ultimately runs inside
3. [Reference → Repository structure](reference/repository-structure.md)
4. [Contributing → Coding conventions](contributing/coding-conventions.md) and [Development workflow](contributing/development-workflow.md)
5. [Guides → Testing](guides/testing.md) and [Database migrations](guides/database-migrations.md)

### Frontend developers

Working in `frontend/src/`:

1. [Architecture → Frontend](architecture/frontend.md) — route structure, the Workbench feature module, the OpenAPI codegen pipeline
2. [API → Overview](api/overview.md) — base path, auth, error format, pagination
3. [API → Streaming events](api/streaming-events.md) — the SSE contract the Workbench consumes live
4. [Concepts → Charts and displays](concepts/charts-and-displays.md) — the contract the chart renderer implements
5. [Contributing → Coding conventions](contributing/coding-conventions.md)

### AI / agent developers

Extending what the agent can do — a new tool, skill, specialist, metric, or chart type:

1. [Concepts → Tools, skills, and specialists](concepts/tools-skills-and-specialists.md) — the current inventory
2. [Architecture → Agent runtime](architecture/agent-runtime.md) — how a tool call, skill load, or delegation actually executes
3. [Guides → Adding a tool](guides/adding-a-tool.md), [Adding a skill](guides/adding-a-skill.md), [Adding a specialist](guides/adding-a-specialist.md)
4. [Guides → Adding a semantic metric](guides/adding-a-semantic-metric.md), [Adding a chart type](guides/adding-a-chart-type.md)

### Data analysts

Using the Workbench to run analyses and produce reports, not writing code:

1. [Guides → Running an analysis](guides/running-an-analysis.md) — start, stream, evidence, displays, publish, download
2. [Concepts → Evidence and citations](concepts/evidence-and-citations.md) — what a citation does and does not prove
3. [Concepts → Semantic metrics](concepts/semantic-metrics.md) and [Report templates](concepts/report-templates.md)
4. [Guides → Generating reports outside a live run](guides/generating-reports.md) — saved and scheduled reports

### Operators

Running a deployment:

1. [Operations → Deployment](operations/deployment.md) — required services, processes, production configuration
2. [Operations → Database](operations/database.md) and [Backups and retention](operations/backups-and-retention.md)
3. [Operations → Security](operations/security.md) and [Observability](operations/observability.md)
4. [Reference → Environment variables](reference/environment-variables.md)
5. [Operations → Production readiness checklist](operations/production-checklist.md) — before going live

### Contributors

Making a change to this repository:

1. [Contributing → Development workflow](contributing/development-workflow.md)
2. [Contributing → Coding conventions](contributing/coding-conventions.md)
3. [Guides → Testing](guides/testing.md)
4. [Contributing → Pull requests](contributing/pull-requests.md) — the checklist that stands in for this repository's absent CI
5. [Contributing → Documentation guidelines](contributing/documentation-guidelines.md) — what to update when your change touches something documented here
