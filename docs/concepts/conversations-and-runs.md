# Conversations and runs

## Conversation versus run

A **conversation** (`ConversationRecord`) is the durable container: a workspace-scoped
title plus timestamps, owning any number of messages and runs. A **run**
(`AgentRunRecord`) is one execution of the agent loop, described in full in
[agent-runtime.md](../architecture/agent-runtime.md).

The relationship is 1:1 by construction, not by database constraint:
`ConversationStore.create_run` (`backend/app/conversations/store.py`) always creates
exactly one new user message and exactly one new run together, in the same transaction,
setting `run.user_message_id` to that message's ID. There is no code path that attaches
more than one run to the same user message. On completion, a second, separate assistant
message is appended, stamped with `run_id` (not `user_message_id`) — so a conversation's
visible message list is threaded by `conversation_id` order, while `user_message_id` on
the run and `run_id` on the reply are what let you reconstruct which turn produced which
run and which run produced which reply.

## Run states

`RunStatus` (`backend/app/runtime/state.py`):

| Value | Meaning |
|---|---|
| `running` | Actively executing |
| `waiting_for_approval` | Paused at a human-approval checkpoint (see [agent-runtime.md](../architecture/agent-runtime.md#human-approval-checkpoints)) |
| `completed` | Finished with an accepted final answer |
| `failed` | Terminated without producing an answer |

`StopReason` (same file) — set alongside a terminal `RunStatus`:

| Value | Meaning |
|---|---|
| `completed` | Reached a normal finish |
| `max_iterations` | Hit the iteration limit |
| `max_tool_calls` | Hit the tool-call limit |
| `too_many_errors` | Recoverable-error count exceeded its bound |
| `cancelled` | Run was cancelled |
| `fatal_error` | An unrecoverable error terminated the run |

The public API does not reprint these values literally — `AgentRunManager` translates an
internal `running`/limit-based status into a public `"failed"` with an explanatory
message (e.g. "The run reached a runtime limit before producing a final response") rather
than exposing `StopReason` strings directly.

## Messages and observations — a deliberate distinction

A **message** (`MessageRecord`) is one visible, persisted conversation turn — `role`,
`content`, `conversation_id`, and (for an assistant reply) the `run_id` that produced it.

An **observation** (`Observation`, `backend/app/runtime/state.py`) is a result the agent
can consider in a *later iteration of the same run* — the wrapped output of a tool call,
skill load, or delegation. Observations live only in the in-memory, process-local
`AgentState.observations` list for the duration of one run. **They are never persisted
directly.** What survives a run is only the denormalized summary written onto the
completed `AgentRunRecord`: `answer_sources`, `chart_specs`, `answer_caveats`, `metrics`,
and the final answer text (written as a new message only if the run's status is
`completed`). This is a deliberate trade-off, not an oversight — the schema comment on
`answer_sources` states plainly that query identifiers are "minted against a process-local
trace that does not survive a restart," which is exactly why only the extracted, durable
facts are written down, not the raw observation stream that produced them.

## Trace events

The fine-grained record of *everything* a run did — every LLM call, tool call, retry, and
delegation — is a `RunTrace` made of `TraceEvent`s (`backend/app/observability/events.py`),
43 distinct event types spanning run/LLM/tool/memory/delegation/security/approval/
artifact/database-query/analytics-python/chart/report/plan lifecycle moments. **This is
not durable.** The only concrete store is `InMemoryTraceStore`
(`backend/app/observability/in_memory.py`), explicitly documented as process-local and
non-persistent, bounded to the most recent 1,000 traces, evicting oldest on overflow —
traces disappear on an API restart. There is no `TraceRecord` table and no Postgres-backed
implementation anywhere in the codebase. See
[persistence.md](../architecture/persistence.md#messages-and-traces) and
[limitations.md](../reference/limitations.md).

## Working, episodic, and long-term memory

Covered in full in [memory.md](memory.md) — summarized here for context: memory is a
separate, durable concept from observations and traces. A memory record persists across
runs and conversations (scoped to a workspace), while an observation exists only within
one run's lifetime.

## Compaction

"Compaction" in this system refers specifically to the **observation window** the model
sees each iteration, not to memory or to persisted messages. Old observations are never
deleted from `AgentState.observations` — the full history is retained for the life of the
run. Once a running, deterministic `TaskSummary` covers everything older than the most
recent 5 observations (`RECENT_OBSERVATIONS`), context building shows only that recent
window plus the summary; if summarization has fallen behind, it shows the full history
instead of silently hiding anything. Full mechanism, including the typed `TaskSummary`
schema, is in [agent-runtime.md](../architecture/agent-runtime.md#observation-compaction).
Memory records are not compacted at all — each is a discrete row, retrieved by lexical
relevance, never merged or summarized (see [memory.md](memory.md)).

## Persistence and tenant scope

Conversations, messages, and runs are all workspace-scoped
(`ConversationRecord.workspace_id`), enforced the same way every other tenant-owned
resource is — see [authentication-and-tenancy.md](../architecture/authentication-and-tenancy.md).
A bare `run_id` has no workspace of its own; ownership is verified by joining to the
owning conversation. All three tables live in the application database
(`DATABASE_URL`), independent of which analytics database a run happened to query — see
[persistence.md](../architecture/persistence.md#conversations-and-runs).
