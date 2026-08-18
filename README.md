# Autonomous Agent Runtime

A modular Python runtime for building autonomous LLM agents that dynamically decide how to accomplish a goal using tools, skills, observations, and iterative decision-making.

The project focuses on understanding and implementing the core architecture behind autonomous AI agents without relying on high-level agent orchestration frameworks.

## Overview

Traditional AI workflows define the execution path in advance:

```text
Input → Search → Analyze → Generate Report → Output
```

This project takes a different approach.

The application defines the agent's **capabilities and boundaries**, while the LLM decides what action should happen next:

```text
                    User Goal
                        │
                        ▼
                  Agent Runtime
                        │
                        ▼
                   LLM Decision
                        │
            ┌───────────┼───────────┐
            ▼           ▼           ▼
         Use Tool    Load Skill    Finish
            │           │
            ▼           ▼
       Tool Result   Instructions
            │           │
            └─────┬─────┘
                  ▼
              Observation
                  │
                  ▼
Agent State
                  │
                  └──────→ Decide Again
```

## Memory architecture (V3)

Memory is curated context, not execution history. The runtime keeps these concepts separate:

| Concept | Scope and purpose |
| --- | --- |
| Observation | Raw result from the current run; retained in `AgentState`, never made durable automatically. |
| Working memory | Explicit run-local context, such as the active goal; removed when the run ends. |
| Task summary | Compact description of older current-run observations; never persisted as memory by itself. |
| Episodic memory | A useful outcome from one completed run, stored with its source run ID. |
| Long-term memory | Curated stable facts, project context, decisions, preferences, resolved issues, or lessons. |

At run start, `MemoryRetriever` selects at most five historical records using deterministic
keyword overlap, tags, type weighting, recency, and session scope. Global and same-session
records enter the distinct `relevant_memories` context section; other session-scoped records
do not. Retrieval runs once per run, and historical memory is never authoritative over the
current goal or current evidence.

After a successful run, `MemoryWritingPipeline` extracts proposals, applies deterministic
policy, checks normalized duplicates, and only then asks `MemoryManager` to persist accepted
episodic or long-term records. Raw tool output, calculations, transient failures, generic
prose, and private-reasoning markers are rejected. Extractors can only propose candidates;
they cannot write to storage directly.

```text
Run start: Goal → MemoryRetriever → MemoryStore → Relevant Memories → ContextBuilder
Run finish: Outcome → Candidate Extractor → Memory Policy → MemoryManager → MemoryStore
```

The default store is process-local and concurrency-safe. PostgreSQL can be selected for
persistence. Semantic/vector retrieval, embeddings, pgvector, and LLM reranking are not
implemented yet.

### PostgreSQL memory backend

Set `MEMORY_BACKEND=postgres` and an asyncpg `DATABASE_URL` in `.env`, then apply the
schema migration before starting the application:

```bash
alembic upgrade head
```

For example: `DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agent`.
Keep this value out of source control. The FastAPI lifecycle disposes the shared
PostgreSQL connection pool on shutdown; application startup never creates tables.

Longer runs also use a typed task summary to avoid carrying every historical
observation indefinitely. Once `SUMMARY_TRIGGER_OBSERVATIONS` is reached, history that
would leave the `RECENT_OBSERVATIONS` window is compacted. The model receives:

```text
Current Goal + Task Summary + Relevant Memories + Working Memory + Recent Observations
+ Loaded Skills + Runtime Status
```

Raw observations remain intact in `AgentState`. If summarization fails, the run keeps
going and the context falls back to the full observation history rather than dropping
unsummarized evidence.

There is no predefined sequence such as:

```python
search()
analyze()
calculate()
generate_report()
```

Instead, the runtime repeatedly asks the model:

> Given the goal, available capabilities, and observations so far, what is the most useful action to take next?

The runtime then validates and executes that action.

---

## Core Principles

### Autonomous decision-making

The LLM chooses the next action dynamically rather than following a hard-coded workflow.

### Controlled autonomy

The model decides **what** it wants to do.

The runtime decides whether that action is valid, allowed, and executable.

### Tools and skills are different

**Tools** allow the agent to perform actions.

Examples:

```text
calculator
web_search
python_exec
```

**Skills** provide specialized instructions and expertise.

Examples:

```text
research
software_engineering
data_analysis
```

Skills use progressive disclosure. The model initially sees only compact skill metadata and loads the full instructions when a skill becomes useful.

### Provider separation

The agent runtime does not depend directly on a specific LLM provider.

```text
AgentRunner
    │
    ▼
LLMClient
    │
    ├── OpenAI
    └── Future providers
```

### Framework-independent runtime

The core agent loop is implemented directly rather than delegated to an orchestration framework.

The project currently does not depend on LangGraph, LangChain, CrewAI, AutoGen, or the OpenAI Agents SDK.

---

## Architecture

```text
FastAPI
   │
   ▼
AgentRunner
   │
   ├──── Context Builder
   │
   ├──── LLM Client
   │
   ├──── Skill Registry
   │
   └──── Tool Executor
             │
             ▼
        Tool Registry
             │
             ▼
            Tool
             │
             ▼
         Tool Result
```

FastAPI is intentionally kept separate from the agent runtime.

This allows the runtime to eventually be used from:

- HTTP APIs
- CLI applications
- background workers
- WebSockets
- tests
- other Python applications

without coupling agent behavior to FastAPI.

---

## Autonomous Agent Loop

At its core, the runtime follows a simple loop:

```text
Receive goal
    │
    ▼
Create state
    │
    ▼
Build context
    │
    ▼
Ask LLM for next action
    │
    ▼
┌──────────────┬──────────────┬──────────────┐
│   Use Tool   │  Load Skill  │    Finish    │
└──────┬───────┴──────┬───────┴──────────────┘
       │              │
       ▼              ▼
 ToolExecutor     SkillRegistry
       │              │
       ▼              ▼
 ToolResult      Instructions
       │              │
       └──────┬───────┘
              ▼
         Observation
              │
              ▼
         Update State
              │
              ▼
         Decide Again
```

The loop continues until the model finishes the objective or the runtime reaches a configured safety limit.

---

## Runtime Safety

Autonomy is bounded by deterministic runtime controls.

The runtime can enforce limits such as:

- maximum iterations
- maximum tool calls
- maximum recoverable errors
- repeated-action limits

Repeated identical actions are detected to reduce the risk of an agent getting stuck in loops.

Tool failures are returned to the agent as structured observations whenever possible, allowing the model to decide whether to retry, change its approach, use another capability, or stop.

---

## Skills

Skills provide specialized guidance without requiring a separate agent.

Current skills include:

### Research

Guidance for factual investigation, source verification, uncertainty, and evidence quality.

### Software Engineering

Guidance for understanding architectures, debugging, making minimal changes, validating assumptions, and testing software.

### Data Analysis

Guidance for inspecting data, validating quality, performing calculations, interpreting results, and communicating assumptions.

Skills follow a progressive-disclosure model:

```text
Available skill
      │
      ▼
Name + description
      │
      ▼
Agent decides skill is useful
      │
      ▼
Load SKILL.md
      │
      ▼
Full instructions enter context
```

This prevents every skill from consuming context on every request.

---

## Tools

Tools are executable capabilities available to the agent.

The architecture separates tool selection from tool execution:

```text
LLM
 │
 │ chooses
 ▼
AgentAction
 │
 ▼
ToolExecutor
 │
 ▼
ToolRegistry
 │
 ▼
Tool
 │
 ▼
ToolResult
```

Tool results are structured so the agent can distinguish successful execution from failures.

Potential capabilities include:

```text
calculator
web search
code execution
filesystem access
database access
external APIs
```

Some potentially dangerous capabilities may intentionally remain disabled until proper sandboxing and security controls are implemented.

---

## Observability

Agent runs use structured runtime logging to make autonomous behavior inspectable.

Important events include:

```text
agent_run_started
iteration_started
llm_action_selected
skill_loaded
tool_execution_started
tool_execution_finished
tool_execution_failed
duplicate_action_detected
runtime_limit_reached
agent_finished
agent_run_failed
memory_retrieval_started
memory_retrieval_finished
task_summary_started
task_summary_updated
memory_candidate_created
memory_candidate_rejected
memory_candidate_accepted
memory_persisted
```

Each run receives a unique `run_id`, allowing events from concurrent executions to be correlated.

The system intentionally avoids logging private chain-of-thought, secrets, API keys, and other sensitive values.

---

## Project Structure

```text
app/
├── api/
│   ├── routes/
│   └── schemas/
│
├── agent/
│   ├── runner.py
│   ├── state.py
│   ├── models.py
│   ├── context.py
│   ├── prompt.py
│   └── policies.py
│
├── llm/
│   ├── base.py
│   └── openai_client.py
│
├── tools/
│   ├── base.py
│   ├── models.py
│   ├── registry.py
│   ├── executor.py
│   ├── calculator.py
│   ├── web_search.py
│   └── python_exec.py
│
├── skills/
│   ├── registry.py
│   ├── models.py
│   ├── research/
│   ├── software_engineering/
│   └── data_analysis/
│
└── core/
    ├── exceptions.py
    ├── limits.py
    └── logging.py

tests/

scripts/
```

The exact structure may evolve as additional runtime capabilities are introduced.

---

## Getting Started

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd autonomous-agent-runtime
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example configuration:

```bash
cp .env.example .env
```

Configure the required values:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=your_model
MAX_AGENT_ITERATIONS=20
LOG_LEVEL=INFO
```

Never commit `.env` or API keys to Git.

### 5. Start the API

```bash
uvicorn app.main:app --reload
```

The API will be available locally at:

```text
http://localhost:8000
```

FastAPI documentation:

```text
http://localhost:8000/docs
```

---

## Running an Agent

The main endpoint accepts a high-level goal:

```http
POST /agent/run
```

Example request:

```json
{
  "goal": "Calculate the percentage increase from 180ms to 620ms and explain what it means."
}
```

The agent determines which available capabilities are useful and continues working until it considers the objective complete or the runtime stops execution.

---

## Testing

Run the automated test suite with:

```bash
pytest
```

The project also contains manual scenarios for observing real autonomous behavior.

Example scenarios include:

```text
Simple calculation
Data analysis
Skill selection
Tool failure recovery
Unsafe tool input
Duplicate action detection
Stopping behavior
Cross-domain reasoning
```

These scenarios are particularly useful together with structured runtime logs.

---

## Development Roadmap

### V1 — Autonomous Core ✅

- agent execution loop
- structured agent actions
- LLM abstraction
- tool registry
- skill registry
- FastAPI interface

### V2 — Robust Autonomous Runtime 🚧

- structured tool results
- tool executor
- error recovery
- runtime limits
- duplicate-action protection
- dynamic skill loading
- progressive skill disclosure
- structured logging
- context engineering

### V3 — Memory

Planned:

- working memory
- task summarization
- memory abstractions
- persistent memory
- relevant-memory retrieval
- memory writing policies

### V4 — Multi-Agent

Planned:

- subagents
- delegation
- specialist agents
- parallel execution
- result aggregation

### V5 — Agent Environment

Planned:

- sandboxed code execution
- filesystem access
- repository interaction
- shell/environment tools

### V6 — Security & Human Control

Planned:

- permissions
- tool policies
- approval gates
- prompt-injection defenses
- sensitive-action controls

### V7 — Evaluation & Production

Planned:

- agent evaluations
- trajectory analysis
- cost tracking
- latency analysis
- tracing
- production hardening

---

## Why Build the Runtime Directly?

High-level agent frameworks provide useful abstractions, but this project intentionally starts from lower-level primitives.

The objective is to understand how autonomous agent systems actually work:

```text
LLM
+
state
+
context
+
tools
+
skills
+
observations
+
runtime policies
+
memory
+
agent loop
```

Once these primitives are understood and evaluated, higher-level frameworks and agent SDKs can be compared based on what they actually improve rather than being treated as black boxes.

---

## Status

This project is under active development and is intended primarily for learning, experimentation, and exploration of production-oriented autonomous agent architecture.

It is **not yet intended for unsupervised production use**, especially for tools capable of modifying files, executing code, accessing external systems, or performing sensitive actions.

## License

No license has been selected yet.
