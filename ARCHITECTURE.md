# Architecture Guide

## Purpose

This repository is a small autonomous-agent harness. A caller submits a goal, and the
agent runtime repeatedly asks an LLM to choose one next action: call a registered tool,
load a skill, or finish. The LLM chooses the action dynamically; the application does
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
build_context(state, tools, skills)
    |
LLMClient.choose_action(...)
    |
OpenAI function call -> AgentAction
    |
ToolExecutor.execute(tool_name, arguments)
    |
ToolRegistry -> Tool -> ToolResult
    |
use ToolResult observation / load skill / finish
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
- `app/agent/models.py`: defines `AgentAction` and the valid action types: `use_tool`, `load_skill`, and `finish`.
- `app/agent/prompt.py`: holds the concise provider-neutral instructions for choosing one next action without following a fixed workflow.
- `app/agent/context.py`: builds the information given to the LLM: goal, task summary, explicit working memory, recent observations, available tools, available skills, loaded skill content, and runtime status.
- `app/agent/summarization.py`: defines the provider-neutral `TaskSummarizer` contract, deterministic trigger policy, and safe default summarizer.

### Memory: `app/memory/`

- `app/memory/models.py`: defines typed working, episodic, and long-term `Memory` records.
- `app/memory/base.py`: defines the asynchronous storage-only `MemoryStore` contract.
- `app/memory/in_memory.py`: provides the concurrency-safe process-local implementation used in development and tests.
- `app/memory/manager.py`: provides the domain-facing `MemoryManager`, lifecycle logging, and working-memory cleanup.

`AgentRunner` optionally receives a `MemoryManager`. It records the submitted goal as
working memory and clears that run-local record at completion. It never automatically
turns raw observations into memories. The API composes an in-memory manager, leaving
persistent stores as a future substitution.

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
- `app/tools/python_exec.py`: reserved interface for future sandboxed Python execution; it is not registered or executable yet.

### Skills: `app/skills/`

- `app/skills/__init__.py`: marks skills as a package.
- `app/skills/models.py`: defines the compact skill metadata exposed during discovery.
- `app/skills/registry.py`: discovers skill directories from `metadata.json`, exposes compact metadata initially, and loads and caches full `SKILL.md` content when requested.
- `app/skills/{research,software_engineering,data_analysis}/metadata.json`: compact discovery metadata for each skill.
- `app/skills/{research,software_engineering,data_analysis}/SKILL.md`: detailed instructions loaded only after the agent selects that skill.

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

## Extending the System

Add a tool by implementing `Tool`, registering it in `get_tool_registry`, and writing a
focused test. Add a skill by creating a directory containing `metadata.json` and `SKILL.md`;
`SkillRegistry` discovers its metadata automatically. Add another model provider by
implementing `LLMClient`.
