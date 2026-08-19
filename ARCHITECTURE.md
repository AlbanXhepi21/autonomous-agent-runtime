# Architecture Guide

## Purpose

This repository is a small autonomous-agent harness. A caller submits a goal, and the
agent runtime repeatedly asks an LLM to choose one next action: call a registered tool,
load a skill, request a specialist delegation, or finish. The LLM chooses the action dynamically; the application does
not impose a fixed workflow.

FastAPI is only one interface. The runtime in `app/agent/` does not import FastAPI and
can later be reused from a CLI, worker, WebSocket connection, or test.

## Runtime Flow

```text
HTTP request
    |
POST /agent/run
    |
AgentRunner.run(goal)
    |
build_context(state, tools, skills, specialists)
    |
LLMClient.choose_action(...)
    |
OpenAI function call -> AgentAction
    |
use_tool -> ToolExecutor -> ToolResult
delegate -> SequentialSubagentExecutor -> scoped child AgentRunner -> SubagentResult
    |
parent observation / load skill / finish
    |
update AgentState and repeat until complete or iteration limit
```

The runtime owns limits and dispatch. The LLM only selects from the capabilities made
available in the current context.

## Boundaries

- `app/api/` translates HTTP requests into runtime calls and runtime state into HTTP responses.
- `app/agent/` contains provider-neutral execution behavior.
- `app/llm/` isolates model-provider code behind `LLMClient`.
- `app/tools/` exposes executable capabilities through `ToolRegistry`.
- `app/skills/` exposes instructions through progressive disclosure, not execution.
- `app/memory/` separates typed memory domain operations from physical storage.
- `app/core/` contains shared domain errors.

## File Reference

### Project Files

- `.env`: local credentials and runtime values. This file is ignored and must not be committed.
- `.env.example`: safe example of the required environment variables.
- `.gitignore`: excludes credentials, virtual environments, caches, IDE files, and operating-system files.
- `requirements.txt`: runtime and test dependencies.
- `README.md`: short project introduction and setup commands.
- `ARCHITECTURE.md`: this architecture and file guide.

### Application Root

- `app/__init__.py`: marks `app` as a Python package.
- `app/main.py`: creates the FastAPI application and registers the agent router. It contains no agent behavior.
- `app/config.py`: defines the central `Settings` model for the OpenAI key, model, runtime limits, `LOG_LEVEL`, and `LOG_FORMAT` (`pretty` or `json`).

### HTTP Interface: `app/api/`

- `app/api/__init__.py`: marks the API layer as a package.
- `app/api/dependencies.py`: constructs the settings, LLM client, tool registry, skill registry, and `AgentRunner` used by the HTTP layer.
- `app/api/schemas/__init__.py`: marks API schemas as a package.
- `app/api/schemas/agent.py`: defines `AgentRunRequest` (`goal`) and `AgentRunResponse` (answer, iterations, used skills, and completion state).
- `app/api/routes/__init__.py`: marks route modules as a package.
- `app/api/routes/agent.py`: implements the thin `POST /agent/run` endpoint. It passes the goal to `AgentRunner` and serializes the resulting state.

### Agent Runtime: `app/agent/`

- `app/agent/__init__.py`: marks the agent runtime as a package.
- `app/agent/runner.py`: implements `AgentRunner`, the bounded loop that requests an action, records its result, summarizes older history when the deterministic policy triggers, and stops on completion or the configured limit.
- `app/agent/state.py`: defines `Observation`, `TaskSummary`, and `AgentState`, which hold the goal, unique run ID, structured tool results, loaded skill content, summary checkpoint, runtime counters, terminal reason, and final answer.
- `app/agent/models.py`: defines `AgentAction` and the valid action types: `use_tool`, `load_skill`, `delegate`, and `finish`.
- `app/agent/delegation.py`: defines `DelegationRequest`, compact `SubagentResult`, and `SequentialSubagentExecutor`, which creates one isolated, capability-scoped child runtime at a time.
- `app/agent/definition.py`: defines immutable-style specialist identity, capability, and optional runtime-override models; it has no run state.
- `app/agent/registry.py`: discovers specialist definitions in `app/agents/`, validates their declared tools and skills when registries are supplied, exposes compact metadata, and progressively loads `AGENT.md`.
- `app/agent/prompt.py`: holds the concise provider-neutral instructions for choosing one next action without following a fixed workflow.
- `app/agent/context.py`: builds the information given to the LLM: goal, task summary, explicit working memory, recent observations, available tools, available skills, loaded skill content, and runtime status.
- `app/agent/summarization.py`: defines the provider-neutral `TaskSummarizer` contract, deterministic trigger policy, and safe default summarizer.

### Memory: `app/memory/`

- `app/memory/models.py`: defines typed working, episodic, and long-term `Memory` records.
- `app/memory/base.py`: defines the asynchronous storage-only `MemoryStore` contract.
- `app/memory/in_memory.py`: provides the concurrency-safe process-local implementation used in development and tests.
- `app/memory/manager.py`: provides the domain-facing `MemoryManager`, lifecycle logging, and working-memory cleanup.
- `app/memory/postgres.py`: implements the same `MemoryStore` contract with PostgreSQL.

### Database: `app/db/`

- `app/db/session.py`: owns the application-scoped SQLAlchemy async engine and creates short-lived sessions for individual store operations.
- `app/db/models.py`: maps the PostgreSQL `memories` table: UUID ID, JSONB metadata, timestamps, and filter indexes.
- `migrations/`: Alembic environment and initial `20260817_0001` migration. Set `DATABASE_URL` then run `alembic upgrade head`; tables are never created at application startup.

`AgentRunner` optionally receives a `MemoryManager`. It records the submitted goal as
working memory and clears that run-local record at completion. It never automatically
turns raw observations into memories. The API composes the configured store without
exposing the selected backend to `AgentRunner`.

`MEMORY_BACKEND=in_memory` selects the process-local store. `MEMORY_BACKEND=postgres`
selects `PostgresMemoryStore` with `DATABASE_URL`. The dependency layer caches one
store and manager per process; the PostgreSQL engine owns its connection pool, each
store operation opens and closes a short-lived session, and the FastAPI lifespan
disposes the pool at shutdown.

## V3.2 Context Flow

```text
Observations outside recent window ──> TaskSummarizer ──> TaskSummary
Recent observations ───────────────────────────────────> LLM context
Explicit working memories ──────────────────────────────> LLM context
```

`SummaryPolicy` begins summarizing only after `SUMMARY_TRIGGER_OBSERVATIONS` (default
8). It retains `RECENT_OBSERVATIONS` (default 5) verbatim. Should a summarizer fail,
the existing summary remains unchanged and `ContextBuilder` presents all observations
until a valid summary again covers older history. Summary lifecycle events are logged
without emitting full summary content at INFO.

### LLM Integration: `app/llm/`

- `app/llm/__init__.py`: marks LLM integrations as a package.
- `app/llm/base.py`: defines the provider-independent asynchronous `LLMClient` interface.
- `app/llm/openai_client.py`: OpenAI-specific adapter. It turns available tools, skills, and `finish` into strict Responses API function definitions, requests exactly one function call, and converts that call into `AgentAction`.

### Tools: `app/tools/`

- `app/tools/__init__.py`: marks tools as a package.
- `app/tools/base.py`: defines the abstract `Tool` contract: name, description, JSON-schema-like arguments, and asynchronous execution.
- `app/tools/registry.py`: registers tools, retrieves them by name, and exposes their definitions to the context builder and LLM adapter.
- `app/tools/models.py`: defines `ToolResult`, the safe structured outcome of a tool invocation.
- `app/tools/executor.py`: validates tool requests, invokes registered tools, and turns errors into structured failures without exposing exception details to the LLM.
- `app/tools/calculator.py`: implements safe, limited arithmetic using Python's abstract syntax tree rather than unrestricted `eval`.
- `app/tools/web_search.py`: reserved interface for a future web-search provider; it is not registered or executable yet.
- `app/tools/python_exec.py`: thin `python_exec` adapter for restricted local child-process execution.
- `app/tools/commands.py`: thin `run_command` adapter; subprocess policy lives outside the tool.
- `app/tools/repository.py`: bounded tree, search, change-tracking, and fixed read-only Git inspection tools.
- `app/tools/artifacts.py`: explicit `register_artifact` tool; files are not implicitly promoted from ordinary writes.

### Agent Environment: `app/environment/`

- `app/environment/workspace.py`: canonical, root-scoped filesystem operations.
- `app/environment/policy.py`: shared traversal and symlink-escape prevention.
- `app/environment/models.py`: bounded read, write, and listing limits.
- `app/environment/commands.py`: argv-only subprocess executor with timeout, bounded stream capture, and a minimal process environment.
- `app/environment/python.py`: disposable-directory Python child-process executor with source/import policy checks and bounded output.
- `app/environment/policy.py`: command-name, shell-syntax, Python source-size, syntax, and import-allowlist checks.
- `app/environment/repository.py`: source-oriented repository abstraction over `Workspace`; ignores generated/cache trees and exposes fixed read-only Git inspection.

### Artifacts: `app/artifacts/`

- `app/artifacts/models.py`: metadata-only `Artifact` contract, distinct from observations and memories.
- `app/artifacts/store.py`: replaceable `ArtifactStore` and development `WorkspaceArtifactStore`, which copies registered files to `artifacts/<run_id>/`.
- `app/tools/filesystem.py`: registered `list_files`, `read_file`, and `write_file` tools; all path security remains in `Workspace`, not tool-specific code.

### Skills: `app/skills/`

- `app/skills/__init__.py`: marks skills as a package.
- `app/skills/models.py`: defines the compact skill metadata exposed during discovery.
- `app/skills/registry.py`: discovers skill directories from `metadata.json`, exposes compact metadata initially, and loads and caches full `SKILL.md` content when requested.
- `app/skills/{research,software_engineering,data_analysis}/metadata.json`: compact discovery metadata for each skill.
- `app/skills/{research,software_engineering,data_analysis}/SKILL.md`: detailed instructions loaded only after the agent selects that skill.

### Specialist Agents: `app/agents/`

- `app/agents/{research,software_engineer,data_analyst}/metadata.json`: compact specialist metadata including the allowed tools and skills.
- `app/agents/{research,software_engineer,data_analyst}/AGENT.md`: detailed specialist instructions, intentionally not included in normal parent-agent context.

In V4.5 the parent model may select `delegate` or explicit `delegate_parallel`; the runtime validates the target against
this registry, loads exactly that definition, and runs an isolated child `AgentRunner`.
Only the definition's tools and skills are available to the child, and the child receives
only a bounded `DelegationContext`: objective, explicit background, constraints, expected
output, and an opt-in capped list of memory excerpts. Parent observations, loaded skills,
runtime state, and historical-memory retrieval are not copied into the child. Its compact `SubagentResult`
becomes a parent observation separately from `ToolResult`. Parallelism, recursive
delegation, and automatic routing remain intentionally unimplemented.

`delegate_parallel` is never inferred from sequential actions. It carries two or more
independent typed delegation payloads, is limited by `MAX_PARALLEL_SUBAGENTS` (default
3), and uses local async concurrency only. Results remain ordered by request and one
child failure becomes a bounded sibling outcome rather than cancelling successful work.

### Shared Domain Code: `app/core/`

- `app/core/__init__.py`: marks shared core code as a package.
- `app/core/exceptions.py`: defines domain errors for unknown tools, unknown skills, and the reserved iteration-limit exception.
- `app/core/logging.py`: configures standard-library structured development logs and provides safe truncation/redaction helpers.

### Tests: `tests/`

- `tests/__init__.py`: marks the test suite as a package.
- `tests/test_agent.py`: tests state creation and that a fake LLM is stopped at the configured iteration limit.
- `tests/test_tools.py`: tests tool registration and lookup.
- `tests/test_skills.py`: tests skill discovery and loading.
- `tests/test_openai_client.py`: tests conversion of a simulated OpenAI function call into an agent action without using the network.

## Current Capability Set

The only registered executable capability is `calculator`. The model can also load any of
the three local skills or call `finish`. Web search and Python execution are deliberately
not registered until a real provider and sandboxing policy are added.

## V7 Observability, Evaluation, and Reliability

Standard logging remains for human operational diagnostics. `app/observability/`
records sanitized `RunTrace` records for machine-readable run history, including
parent/child lineage, events, spans, and derived usage/latency metrics. The in-memory
store is bounded to 1,000 recent traces and is intentionally non-persistent.

`app/evals/` loads strict JSON datasets, runs deterministic local LLM scenarios, and
evaluates state and trace constraints. Trajectory evaluation derives actions from
trace events without retaining chain-of-thought. Evaluation reports include outcome,
trajectory, and available cost/usage/latency metrics.

`app/reliability/` classifies sanitized failures and supplies the explicit retry
policy. Only bounded transient LLM failures are retried by default; policy denials,
approvals, validation failures, and ordinary tool failures remain non-retryable.

## Extending the System

Add a tool by implementing `Tool`, registering it in `get_tool_registry`, and writing a
focused test. Add a skill by creating a directory containing `metadata.json` and `SKILL.md`;
`SkillRegistry` discovers its metadata automatically. Add another model provider by
implementing `LLMClient`.
