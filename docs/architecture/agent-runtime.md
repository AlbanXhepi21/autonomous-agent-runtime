# Agent runtime

This document covers `backend/app/runtime/` — the actual decision loop, not the run
lifecycle around it (see [backend.md](backend.md#disambiguating-runtime-orchestration-and-composition)
for that distinction). Throughout, each mechanism is labeled:

- **(a) Runtime-enforced** — checked in code against state the model cannot alter,
  regardless of what the model requests.
- **(b) Model instruction** — a prompting/tool-description convention the model is asked,
  but not forced, to follow.
- **(c) Human-approval checkpoint** — a runtime-enforced gate whose release requires a
  person's decision, not just code.

## The one-next-action loop

`AgentRunner.run()` (`backend/app/runtime/runner.py`) loops while
`state.iteration_count < max_iterations`. Each iteration:

1. Build context (`ContextBuilder.build`, `runtime/context.py`) — goal, recent
   observations, loaded skills, investigation plan, remaining budget.
2. Call the model for one decision (`LLMClient.choose_decision`), inside a retry loop that
   classifies failures and can inject a runtime correction on invalid output before
   retrying.
3. Dispatch the returned `AgentAction` on its `action_type`.
4. Run the observation-compaction check (every iteration, regardless of action type).
5. Stop if the run completed, was paused for approval, or hit a stop reason; otherwise
   continue.

Dispatch (`_apply_action`) is a plain if/elif chain on `action_type`, not a lookup table —
this is safe only because `AgentAction`'s action-type field is a closed `Literal`
validated by Pydantic before dispatch ever runs. **(a)**

## Action types

`AgentAction.action_type` (`backend/app/contracts/actions.py`) is one of exactly five
values, each with its own required-field validation enforced at construction time (a
`finish` action requires `final_answer`; only `finish` may carry `citations`/`caveats`;
`delegate_parallel` requires at least two delegations):

| Action | Effect |
|---|---|
| `use_tool` | Runs a registered tool through the tool executor (see below) |
| `load_skill` | Loads a skill's Markdown instructions into the run's state |
| `delegate` | Runs one specialist sequentially as a child agent |
| `delegate_parallel` | Runs multiple specialists concurrently |
| `finish` | Proposes a final answer — gated by [Finish behavior](#finish-behavior), not applied immediately |

## Tool execution

A `use_tool` action passes through `ToolExecutor` (`backend/app/tools/execution/`) as a
fixed pipeline: resolve the tool → validate its arguments against a hand-rolled JSON-schema
subset (required fields, `additionalProperties: false`, primitive type checks — this runs
**in addition to** the JSON-schema-shaped function-calling contract OpenAI itself enforces,
not instead of it) → check authorization policy → run it. **(a)**

Every outcome — success or failure — becomes a `ToolResult`, never a raised exception
visible to the model: `ToolInputError` and `ToolExecutionError` map to specific failure
categories, and any other exception is converted to a generic message so internals are
never echoed back. Each result is recorded as an `Observation`
(`state.observations`), which is the *only* thing later verification (see
[Finish behavior](#finish-behavior)) treats as evidence. **(a)**

## Skills and specialists

**Skills** (`backend/app/skills/`) are Markdown instruction bundles, not code. A
`load_skill` action reads and caches the skill's text, stores it into
`state.loaded_skills`, and clears the duplicate-action tracking window (loading a skill is
treated as a genuine change of approach). On the next context build, the full instruction
text appears under `loaded_skills` for the model to read. Whether the model chooses to
load a skill at all is **(b)** — nothing in the loop requires it before acting.

**Specialists** (`backend/app/resources/specialists/`, discovered by
`AgentRegistry` in `runtime/registry.py`) are sub-agents invoked via `delegate`/
`delegate_parallel`. Delegation builds a genuinely separate child `AgentRunner` with:

- **Structural capability scoping**: `ToolRegistry.restricted_to(allowed_tools)` and
  `SkillRegistry.restricted_to(allowed_skills)` construct *new registries containing only
  the granted names* — an ungranted tool is not filtered out at call time, it simply does
  not exist in the child's registry, so calling it raises the same "unknown tool" error a
  typo would. **(a)**
- **A hard depth limit**: the child is built with `agent_depth=1` and
  `delegation_enabled=False`; combined with the default `max_agent_depth=1`, a specialist
  cannot itself delegate further under default configuration. **(a)**
- **Independent iteration and duplicate-action limits** scoped to the child, capped by
  `max_subagent_iterations` regardless of what the specialist's own definition requests.
  **(a)**
- **Approval gates that still apply to specialists**: filesystem-write, command-execute,
  python-execute, and artifact-creation capability gates are added ahead of a specialist's
  own allow-rules, so a specialist cannot use `with_specialist()` grants to bypass human
  approval. **(a) / (c)**
- **A narrow result returned to the parent**: the parent never sees the child's own
  observations or iteration history — only a bounded summary (answer/outcome, error,
  iteration count, tool-call count, duration, stop reason). This is the actual isolation
  boundary between a parent run and its delegated work.

## Iteration / tool / error limits

Every limit lives in `RuntimeLimits` (`backend/app/core/limits.py`) and is checked against
a counter on `AgentState` that the model has no way to write to directly:

| Limit | Default | What happens on breach |
|---|---|---|
| `max_iterations` | 8 | Loop exits; run stops with `MAX_ITERATIONS` |
| `max_tool_calls` | 16 | Run stops with `MAX_TOOL_CALLS`; the requested tool is not executed |
| `max_recoverable_errors` | 3 | Run stops with `TOO_MANY_ERRORS` |
| `max_consecutive_duplicate_actions` | 2 | See [Duplicate-action detection](#duplicate-action-detection) |
| `max_parallel_subagents` | 3 | Delegation rejected, recorded as a limit hit |
| `max_delegations_per_run` | 8 | Delegation rejected, recorded as a limit hit |
| `max_subagent_iterations` | 6 | Folded into the *child's* own iteration cap at construction |
| `max_agent_depth` | 1 | Delegation rejected before it starts — see [Specialists](#skills-and-specialists) |
| `max_finish_redirects` | 2 | A `finish` that would otherwise be redirected again is instead force-accepted, with the gap disclosed as a caveat |

All of the above are **(a)** — none depend on the model's cooperation, and none raise an
uncaught exception on breach; each maps to a defined stop reason or a redirected/failed
observation the model can see and react to.

## Duplicate-action detection

Every tool call is fingerprinted as a SHA-256 hash of its canonical JSON form (tool name +
sorted-key arguments) — an exact-match check, not a semantic one. The runtime counts only
*immediately consecutive* repeats of the same fingerprint; once the count reaches
`max_consecutive_duplicate_actions` (default 2), the tool is **not executed** — a failure
observation tells the model to change its approach, and the call does not count against
`max_tool_calls`. Delegation has an identical, independent fingerprint/threshold pair.
Loading a skill resets the tool-duplicate window. **(a)** — this is exact hashing in code,
not the model self-policing repetition.

## Observation compaction

Old observations are **never deleted** — `state.observations` retains the full history for
the life of the run. What changes is only what the model *sees*: once a running summary
covers everything older than the most recent `RECENT_OBSERVATIONS` (default 5) entries,
context building shows just that recent window plus the summary; if summarization has
fallen behind, it falls back to showing the entire history rather than silently hiding
anything. Compaction is a context-view replacement, not data loss. **(a)**

### Typed task summaries

`TaskSummary` (`backend/app/runtime/state.py`) is a real Pydantic model with five fields:
`goal`, `progress`, `unresolved_questions`, `important_decisions`, `failures_or_blockers`,
plus bookkeeping (`last_updated_iteration`, `summarized_observation_count`). The shipped
implementation, `DeterministicTaskSummarizer`, is non-LLM: for each observation being
folded in, it appends a short outcome line to either `progress` or
`failures_or_blockers` and truncates both to the last 8 entries. **It never populates
`unresolved_questions` or `important_decisions`** — those fields exist in the schema for a
future LLM-backed summarizer, but the production wiring
(`composition/providers/runtime.py`) only ever constructs the deterministic one. A
summarizer exception is caught and logged; the run continues on its last-known-good
summary rather than halting. **(a)**, with two schema fields currently unused by design of
the shipped default.

## Finish behavior

A `finish` action is **not trusted on arrival.** Before anything terminal happens,
`evaluate_finish()` (`backend/app/runtime/planning.py`) runs:

- If the run never created an investigation plan, finish is accepted immediately — this
  check is a no-op for simple factual questions.
- If a plan exists, any question or required output still `pending` is "missing." A
  `detailed_report` request class additionally requires at least one created table output.
- If nothing is missing, finish is accepted.
- If something is missing but the runtime's own budget is nearly exhausted, or the run has
  already been redirected `max_finish_redirects` times, finish is force-accepted anyway
  with the gap disclosed as a caveat — the run is never allowed to loop forever chasing an
  unreachable plan.
- Otherwise the finish is **rejected**: nothing terminal happens, the model gets an
  observation explaining what's still open, and the loop continues.

Crucially, whether an investigation-plan item counts as legitimately resolved is itself
independently checked, not taken from the model's own status update — see
[Investigation planning](#investigation-planning) below. **(a)** — the model's prose in
`final_answer` is never fact-checked, but a claim that a plan item is "answered" or a
display is "created" is checked against observations the runtime itself recorded before
the finish can be accepted as complete.

## Investigation planning

`InvestigationPlan` / `AnalysisQuestion` / `PlannedOutput`
(`backend/app/contracts/investigation.py`) are wired bidirectionally into the loop, not
merely defined:

1. The model writes a plan via the `update_investigation_plan` tool, which validates shape
   only — it does not judge truth of any status.
2. The runtime **reconciles** the plan before storing it: a question the model marks
   "answered" is kept only if its cited evidence IDs match a query this run actually
   executed successfully (`query_database`); an output marked "created" is kept only if
   its display ID matches a chart this run actually produced (`create_chart`). Anything
   that doesn't check out is reset to "pending" and its fabricated evidence is cleared.
   "Blocked" is treated as an honest disclosure and is never second-guessed.
3. The reconciled plan is shown to the model every iteration, outside the observation
   compaction window, so it stays visible regardless of context size.
4. It gates `finish`, as described above.

Whether the model creates a plan at all is **(b)** — tool descriptions recommend it for
non-trivial requests, but a model that never calls `update_investigation_plan` bypasses
this gate entirely (finish then behaves as it always did, with no plan to check against).
The reconciliation and gating mechanics themselves are **(a)**.

## Human approval checkpoints

Approval is gated by **capability**, not by tool name or action type directly. Four
capabilities require approval by default regardless of environment:
`FILESYSTEM_WRITE` (`write_file`), `COMMAND_EXECUTE` (`run_command`), `PYTHON_EXECUTE`
(`python_exec`), and `ARTIFACT_CREATE` (`register_artifact`). A separate risk classifier
can additionally require approval for other actions it scores `HIGH` (for example,
filesystem/command execution in a production security environment), and can outright
**deny** — not merely gate — anything touching a resource identifier that looks
production-like (`prod/`, `.prod`, `live`). **(a)**

When a gated tool call is attempted, the run is suspended: a redacted `ApprovalRequest`
(large content replaced by size+hash, secrets replaced entirely) and a private checkpoint
carrying the exact action are stored, and the run's status becomes "waiting for approval"
— it does not keep looping. If no approval store is configured at all, the action is
denied outright rather than silently allowed. **(c)**

Resuming after a human decision re-validates the action against **current** policy and
re-checks its fingerprint against what was actually approved before executing anything —
a stale or policy-invalidated approval is refused rather than trusted blindly, and only
the runtime itself (holding a private execution token) can invoke the approved path, so no
other caller can use the approval API to bypass the gate. **(a)** enforcing the release of
a **(c)** checkpoint.

## Summary: what the model can and cannot do

| The model can... | The model cannot... |
|---|---|
| Choose which tool, skill, or specialist to use next | Invent a sixth action type, or a `finish` without `final_answer` |
| Write any prose into `final_answer` | Force a plan item to count as answered without matching evidence in the run's own observations |
| Decide whether to create an investigation plan at all | Exceed any iteration/tool/error/delegation/depth limit |
| Retry a failed approach | Repeat the exact same action more than `max_consecutive_duplicate_actions` times in a row |
| Request a gated action (filesystem write, command, Python, artifact creation, high-risk) | Execute it without a human's approval, or reuse a stale/mismatched approval |
