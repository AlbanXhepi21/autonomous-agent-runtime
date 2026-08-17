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

## Memory (V3)

Memory is separate from run observations and does not alter the LLM context yet. The
runtime may use a `MemoryManager` for run-local working memory, while the manager owns
the domain operations and delegates storage to a `MemoryStore` implementation.

```text
AgentRunner → MemoryManager → MemoryStore → InMemoryMemoryStore
```

The initial store is process-local and concurrency-safe. It supports typed `working`,
`episodic`, and `long_term` memories; only explicitly created records are memories.
This leaves a stable boundary for a future persistent implementation such as Postgres.

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
