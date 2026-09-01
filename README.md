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

## Contents

- [What it does](#what-it-does)
- [How the agent works](#how-the-agent-works)
- [The Data Analyst Workbench](#the-data-analyst-workbench)
- [Reporting](#reporting)
- [Parameterized metric reruns](#parameterized-metric-reruns)
- [Memory](#memory)
- [Multi-agent delegation](#multi-agent-delegation)
- [Tools](#tools)
- [Security](#security)
- [Observability and evaluation](#observability-and-evaluation)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Testing](#testing)
- [Design principles](#design-principles)
- [Status and known limitations](#status-and-known-limitations)

---

## What it does

Ask the Workbench a question in plain language:

> "Show payment failures by payment method and failure reason for 2026."

The agent inspects the schema it needs, writes and validates its own SQL, runs it against
a read-only PostgreSQL analytics database, and returns a written answer with a chart, a
table, cited evidence for every figure, and any genuine limitations of what it found. The
whole exchange streams to the browser over SSE as it happens.

From there:

- **Export** the completed run as a PDF or Word report, using one of five templates. The
  document is assembled deterministically from what the run already produced — no further
  model call, and the two formats are guaranteed to state the same facts because they are
  written from one canonical compiled document.
- **Recompute** a report's figures for a different period, grouping or filter, again
  without a model call — the runtime compiles a metric definition into validated SQL, not
  by replaying the original ad-hoc query.
- **Start a new investigation** when what you actually want is a fresh question answered
  for a new period, which is the one path that legitimately involves the model again.

Underneath the Workbench is a general-purpose agent runtime: given a goal, it repeatedly
asks an LLM to choose one next action — use a tool, load a skill, delegate to a specialist,
or finish — until the objective is met or a runtime limit is reached. The Workbench is one
consumer of that runtime; nothing about the agent loop is analytics-specific.

## How the agent works

Traditional agent pipelines fix the steps in advance:

```text
Input → Search → Analyze → Generate Report → Output
```

This runtime does not. The application defines the agent's *capabilities and boundaries* —
which tools exist, which skills can be loaded, which specialists can be delegated to, and
what the runtime will and will not allow — and the model decides, turn by turn, what to do
next:

```text
                    User Goal
                        │
                        ▼
                  Agent Runtime
                        │
                        ▼
                   LLM Decision
                        │
            ┌───────────┼───────────┬───────────┐
            ▼           ▼           ▼           ▼
         Use Tool    Load Skill   Delegate     Finish
            │           │           │
            ▼           ▼           ▼
       Tool Result  Instructions SubagentResult
            │           │           │
            └─────┬─────┴─────┬─────┘
                  ▼
              Observation
                  │
                  ▼
              Agent State
                  │
                  └──────→ Decide Again
```

The loop is bounded by deterministic runtime controls, not by asking the model to behave:
maximum iterations, maximum tool calls, maximum recoverable errors, and repeated-action
detection all stop a run regardless of what the model wants to do next. A tool failure
becomes a structured observation handed back to the model, which can retry, change
approach, or give up cleanly — the runtime does not retry blindly on the model's behalf.

The core loop has no dependency on FastAPI, so it can be driven from an HTTP API, a CLI, a
background worker, or a test, without coupling agent behavior to any one interface.

```text
FastAPI
   │
   ▼
AgentRunner
   │
   ├──── Context Builder
   ├──── LLM Client
   ├──── Skill Registry
   └──── Tool Executor
             │
             ▼
        Tool Registry → Tool → Tool Result
```

Provider access goes through one `LLMClient` interface; the runtime does not depend
directly on OpenAI or any other vendor. No high-level agent orchestration framework
(LangGraph, LangChain, CrewAI, AutoGen, the OpenAI Agents SDK) is used — the loop above is
implemented directly, which is a deliberate choice to understand what such a framework
would actually be abstracting over.

## The Data Analyst Workbench

```text
Next.js Workbench → FastAPI → Agent Runtime / Conversation History / Public Trace
                              ├─ Skills, memory, SQL, bounded Python, artifacts
                              └─ PostgreSQL analytics database (read-only)
```

The Workbench is a Next.js application (`frontend/`) that talks to the backend
(`backend/`) over a versioned HTTP API and an SSE event stream. It provides chat history,
live run progress, public trace inspection, validated analytical displays with an explore
panel, cited evidence and stated limitations shown beside each answer, report export to
PDF and Word, controls for recomputing a report's figures over a different period, a
read-only schema explorer, and a developer-only memory inspector gated behind
`WORKBENCH_DEVELOPER_MODE`.

Run both halves locally:

```bash
# terminal 1 — backend
cd backend
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
./scripts/run_api_dev.sh

# terminal 2 — frontend
cd frontend
cp .env.local.example .env.local
npm install && npm run dev
```

`./scripts/run_api_dev.sh` watches only backend source under `app/` and excludes generated
workspace payloads, so a long-running analytics query does not trigger a reload mid-run.
`NEXT_PUBLIC_API_BASE_URL` defaults to `http://localhost:8000`; the backend's
`ANALYTICS_UI_FRONTEND_ORIGINS` must include the frontend's origin (the default does).

### Reading data safely

The data-analyst specialist connects to `ANALYTICS_DATABASE_URL` — a separate connection
from the runtime's own `DATABASE_URL` — and is deliberately restricted to a narrow set of
capabilities:

- `list_tables`, `describe_table`, `get_table_relationships`, and a deterministic
  `search_schema`, so the model orients itself before writing a query.
- `query_database`, which accepts exactly one `SELECT` or `WITH … SELECT` statement. It is
  parsed into an AST and validated — no mutation, no session-changing statement, no
  system-schema access, no multiple statements, no unsafe PostgreSQL function calls — then
  executed inside a read-only transaction with a server-side timeout and bounded result
  rows and bytes. Application-level validation is a second line of defense; the intended
  deployment also grants the connection role only `SELECT` at the database level:

  ```sql
  CREATE ROLE analytics_reader LOGIN PASSWORD 'use-a-secret-manager';
  GRANT CONNECT ON DATABASE analytics TO analytics_reader;
  GRANT USAGE ON SCHEMA public TO analytics_reader;
  GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_reader;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO analytics_reader;
  ```

- `analyze_dataset` can run pandas/numpy statistics or produce a Matplotlib chart over a
  small, run-scoped result the analyst already fetched with SQL. The child process
  receives only that data — never database credentials — and has no network, subprocess,
  general filesystem, or package-install access. SQL remains the default for joins and
  aggregation; Python is for bounded post-query work such as distributions, correlations,
  or visualization.
- `create_chart` accepts a bounded, data-only `ChartSpec` — never executable code, HTML,
  or SQL — so a display can only ever be a declarative description of rows the agent
  already fetched.
- `generate_report`, distinct from the PDF/DOCX publishing pipeline below, produces
  evidence-linked `report.md`, `supporting_metrics.json`, and bounded CSV extracts as
  in-run artifacts. Every one records its report type, time period, and source
  `query_###` references. `list_metrics` and `describe_metric` expose the same canonical
  business-metric definitions the reruns feature compiles into SQL, so the agent's own
  narrative and a reader's later recompute both rest on one shared definition of what a
  metric means.

For a local, metadata-only check of the analytics connection:

```bash
python -m scripts.inspect_analytics_schema
python -m scripts.inspect_analytics_schema orders
```

### Evidence and citations

An answer references evidence by identifier. The runtime resolves each citation against
the queries the run actually executed and stores the resulting registry beside the answer,
so a citation proves a query ran — it does not independently verify that a sentence in the
narrative was mathematically derived from it. The model never authors a source record.

A citation the run cannot account for is **dropped rather than shown**, and the omission is
logged. Query identifiers are minted against a process-local trace that does not survive a
restart, so the resolved registry is written out in full alongside the run rather than
stored as references that would resolve to nothing later.

A finished answer also carries up to ten **caveats**: genuine limitations the analysis
states about itself — missing or incomplete data, an ambiguous definition, a small sample,
a period the data does not fully cover, source data that may be stale. Caveats are
normalized rather than rejected on the way in, because a finish action arrives after the
work is done, and discarding the whole answer over one caveat that ran a few characters
too long would throw away completed work for a cosmetic reason.

## Reporting

A completed run can be published as a PDF or Word document. Everything the document needs
— the answer, the displays, the resolved evidence, the stated caveats — is already stored
with the run, so publishing is deterministic assembly. It costs no tokens and **never calls
a model**, which is asserted structurally by a test that walks the import graph from the
publishing module and fails if it can reach the LLM package at all.

```text
Completed run
  → evidence resolution
  → canonical compiled report        (one Pydantic model, discriminated on block kind)
  → PDF writer │ DOCX writer         (both read the same blocks, in the same order)
  → artifact verification            (size and SHA-256 recorded)
  → durable artifact store
```

Both renderers consume the same compiled report, so they cannot disagree about a fact — if
they ever do, that is a bug in the compiler, not a difference of opinion between writers.
Nine block kinds are supported: cover, scope, narrative, headline metrics, chart, table,
caveats, evidence appendix, and an explicit page break.

Presentation code may filter rows, reorder them, relabel a column, and format a value it
was given. It may **not** sum, average, count, compute a percentage, take a difference, or
supply a value the run did not produce. Every number a report prints traces back to a query
the run executed.

Five templates ship as JSON resources under `app/resources/report_templates/`, each split
into `metadata.json` (sections, order, per-section limits, orientation, supported formats)
and `theme.json` (palette, fonts, spacing, chart palette) — so a restyle and a new section
cannot break each other:

| Template | Orientation | Shape |
|---|---|---|
| `monthly_business_review` | portrait | recurring management readout |
| `quarterly_review` | portrait | quarterly performance report |
| `annual_review` | portrait | full-year business report |
| `executive_dashboard` | landscape | KPI cards, up to four charts, detail behind a page break |
| `analysis_summary` | portrait | a single investigation, any period |

Charts are drawn server-side with Matplotlib, in the template's theme palette, because the
browser's interactive renderer produces nothing a PDF or DOCX can embed. The PDF supports
running headers and footers, page numbering, repeating table headings across page breaks,
and explicit page breaks. **The PDF is the authoritative deliverable**; the Word document
is an editable convenience copy and says so on its own first page, because nothing stops a
reader from changing a number in Word after export.

The evidence appendix accounts for every query a report rests on: identifier, the runtime's
description of it, execution time, reporting period, tables consulted, returned columns,
row count, the exact rows each figure displayed, and which figures cite it.

Render every template from fixed sample data, with a PNG rendered per page, for reviewing
layout changes without running the agent:

```bash
python -m scripts.preview_reports
```

## Parameterized metric reruns

A reader can change a report's period, grouping, or filters and recompute the factual
sections **without another agent turn**. This does not replay the agent's original SQL —
that statement was written for one specific period and hard-codes it, and was never
reviewed as a reusable query. Instead the runtime compiles a semantic metric definition:

```text
(metric, period, dimension, filters)
  → metric definition        (declares its own SQL, dimensions, and filterable fields)
  → SQL template compilation
  → named bind parameters
  → the same AST validator that guards the agent's own SQL
  → read-only execution
  → a new rerun_### evidence entry
  → immutable metric result
```

The request never becomes SQL text. A dimension resolves to an expression the metric
definition declares; a filter resolves to a declared column and an operator drawn from a
closed set; every value the reader supplies is bound as a parameter, not concatenated. The
compiled statement then passes through the identical validator the agent's ad-hoc SQL is
checked against — being generated by the runtime is not treated as grounds for trust.

Five metrics have compiled definitions today: `revenue`, `orders`, `gross_profit`,
`payment_failure_count`, and `target_attainment`. `target_attainment` joins the
`monthly_targets` table and divides **inside the SQL statement** — a zero or missing target
yields no attainment figure rather than a Python-side division. Recomputed evidence is
numbered in its own `rerun_###` series, so a fresh figure never wears the original run's
query identifier.

Narrative freshness is explicit. Prose written for one period is never silently displayed
next to figures recomputed for another:

| State | Behavior |
|---|---|
| `current` | the prose and the figures come from the same run |
| `pinned_to_original_period` | prose is kept, under a visible warning naming both periods |
| `excluded_from_refreshed_report` | prose is left out, and the report says why |

There is deliberately no fourth state that reuses the prose without a warning. Rewriting it
to match the new period would need a model, and publishing never calls one — to get prose
written for the new period, start a new investigation instead.

## Memory

Memory is curated context, not a log of everything that happened. The runtime keeps these
concepts distinct:

| Concept | Scope and purpose |
| --- | --- |
| Observation | Raw result from the current run; kept in `AgentState`, never made durable automatically. |
| Working memory | Explicit run-local context, such as the active goal; removed when the run ends. |
| Task summary | A compact description of older current-run observations, not persisted as memory. |
| Episodic memory | A useful outcome from one completed run, stored with its source run ID. |
| Long-term memory | Curated stable facts, decisions, preferences, or lessons. |

At run start, `MemoryRetriever` selects at most five historical records using deterministic
keyword overlap, tags, type weighting, recency, and session scope — no embeddings, no
vector search. Retrieval runs once per run and is never treated as authoritative over the
current goal or current evidence.

After a run finishes, `MemoryWritingPipeline` extracts candidate memories, applies
deterministic policy, checks for normalized duplicates, and only then persists accepted
episodic or long-term records. Raw tool output, calculations, transient failures, generic
prose, and anything resembling private reasoning are rejected before they can become a
memory. Extractors can only propose candidates; they cannot write to storage directly.

```text
Run start:  Goal → MemoryRetriever → MemoryStore → Relevant Memories → ContextBuilder
Run finish: Outcome → Candidate Extractor → Memory Policy → MemoryManager → MemoryStore
```

The default store is process-local. Setting `MEMORY_BACKEND=postgres` with an asyncpg
`DATABASE_URL` switches to durable storage after `alembic upgrade head` has been applied;
tables are never created at application startup.

Longer runs also use the task summary to avoid carrying the full observation history
indefinitely: once `SUMMARY_TRIGGER_OBSERVATIONS` is reached, older observations outside
the `RECENT_OBSERVATIONS` window are compacted. If summarization ever fails, the run keeps
going and falls back to the full observation history rather than dropping evidence. The
model receives:

```text
Current Goal + Task Summary + Relevant Memories + Working Memory + Recent Observations
+ Loaded Skills + Runtime Status
```

## Multi-agent delegation

The parent agent decides whether delegation is useful; the runtime validates and bounds
that choice. There is no keyword-based specialist routing and no fixed
research-then-review workflow imposed from outside the model's own decision.

```text
Parent Agent → delegate / delegate_parallel → scoped specialist AgentRunner
             ← bounded SubagentResult       ← its own tools, skills, and decisions
```

A **tool** is an executable capability, like the calculator. A **skill** is progressive
guidance an agent may load for itself. A **subagent** is an independent, bounded run of the
same runtime, selected for a clearly scoped objective.

Specialist definitions live under `app/resources/specialists/` and grant a child only its
own listed tools and skills — parent capabilities and any skills the parent already loaded
are not inherited. The child receives only a typed delegation context (objective, explicit
background, constraints, expected output, and opt-in memory excerpts), never the parent's
transcript or unrestricted historical memory.

Delegation can be sequential (`delegate`) or explicitly parallel (`delegate_parallel`),
capped by `MAX_PARALLEL_SUBAGENTS`. `MAX_AGENT_DEPTH` bounds how deep delegation can nest;
`MAX_DELEGATIONS_PER_RUN` and `MAX_SUBAGENT_ITERATIONS` bound total fan-out and per-child
work. The parent always remains responsible for the final answer — a subagent's result
becomes a compact observation, not a substitute for the parent finishing the task.

Skills use progressive disclosure so the model is not paying context cost for guidance it
never uses:

```text
Available skill → name + description → agent decides it's useful → load SKILL.md → full
instructions enter context
```

Skills currently shipped: `research`, `software_engineering`, `data_analysis`, and
`executive_reporting`. Specialists currently shipped: `research`, `software_engineer`, and
`data_analyst`.

## Tools

The architecture separates tool *selection* from tool *execution*: the model only ever
chooses a name and arguments, and a shared executor is what actually validates and runs
anything.

```text
LLM → AgentAction → ToolExecutor → ToolRegistry → Tool → ToolResult
```

- **Workspace filesystem** — `list_files`, `read_file`, `write_file` operate only inside
  `AGENT_WORKSPACE_ROOT`. Every relative path is canonicalized; absolute paths, traversal
  outside the root, and symlinks resolving outside it are all rejected. Reads, writes, and
  listings are bounded by `MAX_FILE_READ_BYTES`, `MAX_FILE_WRITE_BYTES`, and
  `MAX_LIST_FILES`. Only the software-engineer specialist is granted write access.
- **Controlled command execution** — `run_command` is argv-only: an allowlisted command
  name (`COMMAND_ALLOWLIST`, default `pytest`) plus an `args` array, never a shell string.
  Commands run in the workspace with a minimal environment — host API keys and database
  credentials are not forwarded — bounded by `COMMAND_TIMEOUT_SECONDS` and
  `MAX_COMMAND_OUTPUT_BYTES`.
- **Restricted local Python** — `python_exec` runs short source in a separate `python -I`
  child process, never inside the FastAPI process, using a disposable directory deleted
  after the result is collected. Imports are limited to `PYTHON_EXEC_ALLOWED_IMPORTS`
  (default `math, statistics, json, datetime, collections`); source, time, and output are
  each bounded. This is restricted local execution for development, **not** a
  hostile-code sandbox — there is no OS-level filesystem or network isolation.
- **Repository tools** — `get_repository_tree`, `search_files`, and `get_changed_files`
  give the software-engineer specialist a bounded, read-mostly view of the repository,
  excluding generated and cache directories. `git_inspect` is limited to fixed read-only
  `status`, `diff --stat`, and recent-log commands — it cannot commit, push, reset, clean,
  or checkout.
- **Artifacts** — an agent writes a file with the normal workspace tools, then calls
  `register_artifact` to copy it into a durable, downloadable record. See
  [Artifacts and durable downloads](#artifacts-and-durable-downloads) below.

### Artifacts and durable downloads

Artifacts are explicit, user-consumable outputs — not execution observations and not
memory. Registering one copies the file to a provider-independent storage key:

```text
workspace/artifacts/<run_id>/<artifact_id>/<name>
```

The run response returns metadata only (ID, name, storage key, type, media type, size,
SHA-256, status, run ID, creation time) and never embeds file content in agent state.
`GET /artifacts/{artifact_id}` resolves only a validated registered ID, never an arbitrary
filesystem path.

Registration is two steps on purpose: the record is created `pending`, the bytes are
copied and measured, and only then does it become `ready`. Retrieval ignores anything not
ready, so an interrupted write leaves an unusable row rather than a link to a partial file.

`ARTIFACT_BACKEND=in_memory` keeps records in the process that made them — fine for tests
and single-process development, but every download link is lost at restart.
`ARTIFACT_BACKEND=postgres` records them durably in the runtime database instead, so a
link outlives the process. Files written before durable records existed can be recovered
under their original IDs with `python -m scripts.backfill_artifacts --apply`. Retention is
recorded (`expires_at`) but not yet enforced — nothing sweeps expired artifacts.

## Security

Security is defense in depth: the LLM proposes an action, and deterministic runtime
controls decide whether it is permitted, requires approval, or is denied.

```text
Agent action → capability normalization → risk classification → SecurityPolicy
             → allow / require approval / deny → tool policy → environment boundary
```

Specialist definitions grant only named tools and skills. `ToolExecutor` is the common
execution gate; workspace paths, command allowlists, restricted Python, repository
controls, and artifact validation are independent downstream checks layered on top of it.
Every applicable layer must allow the action for it to proceed.

- **Risk classification and approval** — risk is typed and runtime-derived (`low`,
  `medium`, `high`, `critical`) from semantic capability, resource, environment, and
  runtime identity, never from a model's own claim that an action is safe. A sensitive
  action can create an action-bound approval request with a safe summary and a
  fingerprint; approving it executes only that exact persisted action, once. A rejection
  becomes an observation, so the agent can choose a different approach.
- **Trust boundaries and prompt injection** — system and on-disk agent-definition
  instructions are trusted. User requests are task input. Files, repository data, web
  output, tool output, and retrieved memory are evidence with explicit provenance and are
  never allowed to grant permissions, alter risk, change policy, reveal secrets, or bypass
  approval. Heuristic injection indicators are diagnostic only — prompt injection is not
  treated as a solved problem.
- **Credential isolation** — tools use logical `SecretReference` names (for example
  `github.default`); a trusted `CredentialProvider` resolves the actual value internally.
  Raw secrets never reach LLM context, agent state, memory, approvals, artifacts, or child
  process environments. Known values and common credential patterns are redacted from logs
  and observations; artifacts reject common secret files and detected credential material.

**Known limitations, stated plainly:** the credential provider is local, with no rotation
or central auditing. Approval endpoints assume an authenticated deployment boundary that
does not exist yet. Restricted Python and command execution are development controls, not
a hardened VM or container sandbox. File-backed approvals use local-process locking and
would need transactional shared persistence for a multi-process deployment.

## Observability and evaluation

Every run emits a sanitized, machine-readable `RunTrace` — kept separate from human-facing
application logs — covering run lifecycle, LLM calls, tool execution, skill loads, memory
activity, summarization, delegation, security decisions, approvals, and artifact events.
Child traces carry their own `run_id` and retain `parent_run_id`. `GET /runs/{run_id}/trace`
returns the sanitized trace while the process is running; the store is in-memory, so traces
do not survive a restart.

The trace also derives usage, latency, and estimated cost: LLM decisions can report
provider-neutral token usage, and a versioned `PricingRegistry` prices supported models.
Unsupported models simply leave cost as `null` rather than guessing. Parent/child
aggregation keeps root wall-clock latency separate from summed child execution time.

The runtime classifies failures and retries only bounded transient LLM failures (timeouts,
rate limits, provider faults, one structured-output repair). Security denials, approval
decisions, validation errors, and ordinary tool failures are never automatically retried.

`evals` runs outcome-based JSON suites against a local scripted LLM, so CI needs no API key
and no model call:

```bash
python -m evals.runner --suite basic
python -m evals.runner --case basic.calculate_2_plus_2
python -m evals.runner --all --json-output report.json
```

Each result carries its trace reference for failure investigation, and evaluations also
derive a sanitized action trajectory — bounding iterations, tool calls, delegation depth,
repeated actions, and stopping behavior. A separate benchmark harness compares recorded
real-model runs against ground truth for the analytics domain specifically:

```bash
python -m evals.analytics_runner \
  --ground-truth ../DataGenerator/generator/ground_truth/scenarios.json \
  --recordings benchmark-recordings.json \
  --json-output benchmark-current.json \
  --markdown-output benchmark-current.md \
  --previous benchmark-previous.json
```

This command is offline and never calls a model itself; recordings are produced separately
by running real questions through the configured runtime first. `backend/evals/datasets/`
holds 26 public benchmark questions across analytics basics, sales, profitability,
marketing, customers, operations, inventory, root cause, security, and reporting. These
suites are deterministic regression checks, not a real-model quality or load benchmark —
they do not establish memory effectiveness, delegation benefit, or end-to-end
prompt-injection resistance. See [`docs/V7_FINAL_REPORT.md`](docs/V7_FINAL_REPORT.md) for a
fuller production-readiness review.

## Project structure

The repository holds two peers: `backend/` (FastAPI and the agent runtime) and `frontend/`
(the Next.js Workbench). Each backend package owns one concern, and the import graph is
acyclic — asserted by a test rather than documented and hoped for.

```text
backend/app/
├── api/              HTTP routes and request/response schemas
├── composition/      builds the object graph; the only place wiring lives
├── contracts/        leaf package: actions, answers, run protocols
├── core/             leaf package: domain errors, limits, logging
│
├── runtime/          the bounded agent loop, context, delegation, prompt
├── llm/              provider adapters behind one LLMClient interface
├── tools/            executable capabilities + execution/observers
├── skills/           progressive-disclosure instructions
├── memory/           working, episodic and long-term memory
├── environment/      workspace, subprocess and Python sandboxing
├── security/         capabilities, risk, approvals, credentials, trust
├── reliability/      failure classification and retry policy
├── observability/    sanitized traces, metrics, the evidence ledger
│
├── analytics/
│   ├── schema/       read-only schema discovery and the allowlist policy
│   ├── sql/          AST validation and read-only execution
│   ├── semantics/    metric definitions, parameters, SQL compilation
│   └── presentation/ charts, the compiled report model, PDF/DOCX writers
│
├── orchestration/    run lifecycle, publishing, metric reruns
├── artifacts/        metadata-only records and their file provider
├── conversations/    durable chat history
├── db/               SQLAlchemy models and the shared session factory
└── resources/        skills, specialists and report templates as data

frontend/src/
├── app/                          Next.js app router pages
├── features/workbench/           Workbench UI: components, hooks, display logic
└── lib/api/                      typed HTTP client generated from the OpenAPI schema
```

`contracts/` and `core/` are leaves: they exist to be depended on and may only import each
other. `analytics/` imports only `contracts`, `core`, and `resources` — which is what keeps
the report writers from reaching run-level data and choosing their own facts, and is
enforced by a structural test rather than convention.

Non-Python assets — skills, specialists, report templates — live under `app/resources/`
and are discovered at runtime, so adding one is a JSON or Markdown file, not a release.

## Getting started

```bash
git clone <your-repository-url>
cd autonomous-agent
```

**Backend:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e '.[dev]'
cp .env.example .env
```

Configure `.env`:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5.4-mini
MAX_AGENT_ITERATIONS=20
LOG_LEVEL=INFO

# Runtime persistence: conversations, runs, memory, and artifact records.
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agent
MEMORY_BACKEND=postgres

# `in_memory` loses every artifact record when the process stops, leaving files
# on disk that nothing can hand out. `postgres` keeps the record beside the
# bytes, so a download link survives a restart.
ARTIFACT_BACKEND=postgres

# A published report embeds a rendered chart, so the bound has to admit a
# document rather than a text file.
MAX_ARTIFACT_BYTES=10485760

# The separate, read-only analytics source. Do not reuse DATABASE_URL.
ANALYTICS_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ecommerce_analytics
```

Never commit `.env` or API keys to Git. Apply the schema before starting the API — tables
are never created at startup, and without this migration the `artifacts` table and the
`answer_caveats` column are missing, which makes publishing a report fail:

```bash
alembic upgrade head
```

Start the API:

```bash
./scripts/run_api_dev.sh
```

The API is available at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`.

**Frontend:**

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

### Running the agent directly

The runtime also exposes a plain goal-driven endpoint, independent of the Workbench:

```http
POST /agent/run
```

```json
{
  "goal": "Calculate the percentage increase from 180ms to 620ms and explain what it means."
}
```

The agent determines which available capabilities are useful and works until it considers
the objective complete or a runtime limit stops it.

## Testing

```bash
cd backend && .venv/bin/python -m pytest          # database tests skip cleanly
```

Tests that need a database are marked `postgres` and skip unless the relevant URL is set,
so the suite is green offline. To run them, point at a database with migrations already
applied — the tests never create their own schema:

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agent_test
export ANALYTICS_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ecommerce_analytics
.venv/bin/python -m pytest
```

Some rules are asserted structurally rather than left to review: the import graph stays
acyclic and `contracts`/`core` stay leaves; the report writers cannot reach run-level data;
publishing cannot reach the LLM package; and the committed OpenAPI snapshot must match the
live application, so a schema change that skips `npm run gen:api` fails the build instead
of surfacing at runtime.

Generated documents are verified by reading them back — PDF text with `pypdf`, DOCX
structure with `python-docx` — never by comparing raw bytes, which would only prove the
code is deterministic rather than correct. `scripts/preview_reports.py` renders every
template to page images for the same reason: an automated text assertion passes straight
through a stranded heading or a collapsed table that a rendered page makes obvious.

Frontend checks:

```bash
cd frontend && npm run lint && npm run typecheck && npm test
```

Beyond the automated suite, the repository includes manual agent scenarios — simple
calculation, data analysis, skill selection, tool failure recovery, unsafe tool input,
duplicate-action detection, stopping behavior, cross-domain reasoning — useful alongside
structured runtime logs for observing real autonomous behavior rather than a fixed test
assertion.

## Design principles

**Autonomy is bounded, not trusted.** The model chooses the next action; the runtime
decides whether it is allowed, and stops the run outright if limits are exceeded. Nothing
in the security or resource model depends on the model behaving well.

**Tools, skills, and delegation are different kinds of capability.** A tool executes. A
skill informs. A subagent is an independently bounded run. Conflating them — for instance,
treating a skill load as if it were an action with side effects — is a category error the
runtime does not allow.

**Provenance is structural, not advisory.** A citation resolves against what the run
actually executed or it is dropped; a report figure traces to a query or it is not
printed; a caveat is bounded and normalized rather than silently truncated into something
misleading. These are enforced by contracts and validators, not by asking the model to be
careful.

**Presentation never computes.** Everything downstream of a query result — a chart, a
table, a PDF, a Word document — may filter, reorder, relabel, and format. It may never
sum, average, derive, or invent a value. This is the single rule that makes a published
report trustworthy: every number in it came from a query, not from a renderer's opinion.

**Publishing and recomputation never call a model.** Once a run has produced its answer,
turning that answer into a document — or recomputing its figures for a different period —
is deterministic assembly. This keeps exports free, fast, reproducible, and structurally
incapable of the model quietly rewriting an analysis someone has already signed off on.

**Package boundaries are enforced, not aspirational.** Leaf packages (`contracts`, `core`)
cannot import the runtime. The analytics presentation layer cannot reach run-level facts.
The import graph has no cycles. Each of these is a test, not a comment.

**High-level frameworks are deferred, not rejected.** The agent loop, the tool executor,
and the memory pipeline are built directly so that what a framework like LangGraph or
CrewAI actually provides can eventually be evaluated against a real baseline, rather than
adopted as an unexamined default.

## Status and known limitations

This project is under active development. It is not yet intended for unsupervised
production use, particularly for tools capable of modifying files, executing code,
accessing external systems, or performing other sensitive actions.

Known gaps, stated plainly:

- **Five of twenty-two metrics** have compiled SQL definitions and can be recomputed
  without an agent turn. The remaining seventeen stay documentation for the agent and
  report `is_rerunnable = false`.
- **The agent tends to produce one display per run**, so a question asking for several
  charts usually yields fewer, and a report section may print "This analysis produced no
  charts." The Executive Dashboard template is best seen fully populated through
  `scripts/preview_reports.py` rather than a live run.
- **Web search is an unimplemented interface** — present in the tool contracts, not
  registered or executable.
- **Artifact retention is recorded but not enforced** — `expires_at` is stored on every
  artifact and nothing currently sweeps expired ones.
- **Recursive delegation and automatic specialist routing** remain intentionally absent;
  delegation is always an explicit, model-selected, single-level choice.
- **Trace storage is process-local** with bounded retention and does not survive a
  restart, unlike conversation history, runs, memory, and artifacts, which are durable.
- **Prompt-injection defenses are heuristic, not solved.** Trust boundaries are enforced
  structurally, but injection resistance has not been benchmarked end-to-end.
- The credential provider, approval endpoints, restricted Python/command execution, and
  file-backed approval locking are development-grade controls — see
  [Security](#security) for specifics on what each does and does not provide.

## License

No license has been selected yet.
