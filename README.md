# Autonomous Agent Runtime

A backend agent runtime, built directly on an LLM API rather than an orchestration
framework, paired with a Data Analyst Workbench: a Next.js application where the agent
investigates a read-only e-commerce analytics database, cites its evidence, and publishes
its findings as PDF or Word reports.

The project has two purposes that inform every design choice in it. First, it is a working
analytics product: ask a question in plain language, get a cited answer with charts and
tables, export a report, and later recompute that report's figures for a different period
without spending another model call. Second, it is a study of what an autonomous agent
loop actually requires once naive versions of it are pushed toward correctness — bounded
autonomy, typed memory, multi-agent delegation, a security model, observability, and a
reporting pipeline that cannot let a renderer or a frontend invent a fact.

## What it does

Ask the Workbench a question in plain language:

> "Show payment failures by payment method and failure reason for 2026."

The agent inspects the schema it needs, writes and validates its own SQL, runs it against
a read-only PostgreSQL analytics database, and returns a written answer with a chart, a
table, cited evidence for every figure, and any genuine limitations of what it found —
streamed to the browser over SSE as it happens.

## Key capabilities

- **A bounded agent loop**: given a goal, the runtime repeatedly asks an LLM to choose one
  next action — use a tool, load a skill, delegate to a specialist, or finish — until the
  objective is met or a runtime limit (iterations, tool calls, recoverable errors,
  repeated actions) stops it regardless of what the model wants to do next.
- **A Data Analyst Workbench**: schema discovery, AST-validated read-only SQL, bounded
  Python analysis, data-only chart specs, and semantic metrics that compile to the same
  validated SQL an agent would write by hand.
- **Deterministic reporting**: a completed run publishes to PDF or Word from one canonical
  compiled document — no further model call — and a reader can recompute a report's
  figures for a different period without one either.
- **Multi-agent delegation**: an explicit, model-selected, single-level handoff to a
  scoped specialist (its own tools, skills, and decisions only) — never automatic routing,
  never recursive.
- **Typed, curated memory**: working, episodic, and long-term memory, retrieved by
  deterministic keyword overlap, not embeddings.
- **Defense-in-depth security**: every agent action is capability-normalized and risk
  classified before it's allowed, gated for approval, or denied — see
  [Security](#security) below.
- **Its own authentication and multi-tenant workspaces**: sessions, roles, memberships,
  invitations, and workspace-connected data sources — see
  [`docs/architecture/authentication-and-tenancy.md`](docs/architecture/authentication-and-tenancy.md).

## Architecture, in short

```text
Next.js Workbench → FastAPI → Agent Runtime ⇄ LLM
                              ├─ Tools, skills, memory, security
                              └─ PostgreSQL (app state)  +  PostgreSQL (analytics, read-only)
```

The core loop has no dependency on FastAPI and no dependency on any one LLM vendor — it's
driven through one `LLMClient` interface, and no high-level agent framework (LangGraph,
LangChain, CrewAI, AutoGen) is used underneath it, a deliberate choice to understand what
such a framework would actually be abstracting over. Backend packages each own one
concern, and the import graph is acyclic — asserted by a test, not just documented. The
full breakdown — every package, the request lifecycle, and three diagrams — is in
[`docs/architecture/overview.md`](docs/architecture/overview.md).

## Getting started

```bash
git clone <your-repository-url> && cd autonomous-agent
```

Full, verified setup instructions — prerequisites, exact commands, configuration, and
troubleshooting — are in [`docs/getting-started/`](docs/getting-started/local-development.md).
In short: a Python 3.12 backend (`pip install -e '.[dev]'`, `alembic upgrade head`,
`./scripts/run_api_dev.sh`) and a Next.js frontend (`npm install`, `npm run dev`), against
two PostgreSQL databases — one for application state, one read-only analytics source.

## Documentation

**[`docs/README.md`](docs/README.md) is the full documentation index**, including reading
paths for new users, backend developers, frontend developers, AI/agent developers, data
analysts, operators, and contributors. It covers architecture, feature-level concepts, a
complete reference (environment variables, commands, permissions, limitations), developer
guides, the API contract, and operations — all verified against the current code, not
aspirational.

## Testing

```bash
cd backend && .venv/bin/python -m pytest       # database tests skip cleanly without one
cd frontend && npm run lint && npm run typecheck && npm test
```

Several rules are asserted structurally rather than left to review: the import graph stays
acyclic, publishing can never reach the LLM package, and a committed OpenAPI snapshot must
match the live application. A dedicated documentation test suite
(`backend/tests/contracts/test_documentation.py`) checks every relative link, referenced
path, and inventory table in `docs/` against the code it describes. Full test-tier
breakdown, targeted-run examples, and what needs a real database:
[`docs/guides/testing.md`](docs/guides/testing.md).

## Security

Every agent action is capability-normalized and risk-classified before it's allowed,
gated for human approval, or denied — never trusted because the model claims it's safe.
Filesystem writes, command execution, Python execution, and artifact creation always
require approval, in every environment. Secrets are resolved through logical references,
never passed around as raw strings, and redacted from logs and observations on a
best-effort basis.

**This project is under active development and is not yet intended for unsupervised
production use**, particularly for tools capable of modifying files, executing code, or
accessing external systems. Prompt-injection defenses are heuristic, not solved; the
restricted Python/command execution is process isolation, not a hardened sandbox. Full
trust-boundary breakdown: [`docs/architecture/security-boundaries.md`](docs/architecture/security-boundaries.md).
Operational guidance: [`docs/operations/security.md`](docs/operations/security.md).

## Current limitations

- Only a subset of the registered semantic metrics compile to SQL and can be recomputed
  without an agent turn; the rest are documentation the agent reads before writing its own
  query — see [`docs/concepts/semantic-metrics.md`](docs/concepts/semantic-metrics.md).
- The agent tends to produce one display per run in practice, so a question asking for
  several charts usually yields fewer.
- Web search is an unimplemented, unregistered interface — present in the tool contracts,
  never callable.
- Recursive delegation and automatic specialist routing are intentionally absent.
- Trace storage is process-local and does not survive a restart, unlike conversation
  history, runs, memory, and artifacts, which are durable.
- Setting `SECURITY_ENVIRONMENT=production` is a near-total lockdown, not a mild
  tightening — read this before setting it.

The complete, code-verified list — including how each item was checked — is
[`docs/reference/limitations.md`](docs/reference/limitations.md).

## Contributing

See [`docs/contributing/`](docs/contributing/development-workflow.md) for the development
workflow, coding conventions, pull-request checklist, and documentation guidelines this
repository follows (there is no CI yet, so these checks are currently manual).

## License

No license has been selected yet.
