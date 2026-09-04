# Memory

Agent memory (`backend/app/memory/`) is a durable, cross-run concept — distinct from the
in-run [observations and trace events](conversations-and-runs.md#messages-and-observations-a-deliberate-distinction),
which live and die with a single run.

## The three memory types

`MemoryType` (`backend/app/memory/records.py`) is a three-value enum:

| Type | Intent |
|---|---|
| `working` | Short-lived, current-task context |
| `episodic` | A specific past event or run outcome worth recalling later |
| `long_term` | Durable knowledge meant to persist and inform many future runs |

`MemoryManager` exposes one method per type (`add_working_memory`,
`add_episodic_memory`, `add_long_term_memory`), all writing to the same underlying store
and table — the type is a column value, not a structural difference in storage.

## What's stored

Each memory record (`MemoryRecord`, see [persistence.md](../architecture/persistence.md#memory))
has a workspace ID, a type, free-text `content`, and a `metadata` JSONB blob. There is no
dedicated tags column — tags live inside `metadata["tags"]` by convention. There is no
embedding or vector column on this table at all, which is the schema-level reason
retrieval works the way it does (below), not merely an implementation choice that could be
swapped out without a migration.

## Retrieval is lexical, not semantic

`MemoryRetriever` (`backend/app/memory/retrieval.py`) scores candidate memories by plain
token-overlap:

1. Tokenize the query and each candidate's content + metadata text (lowercase, regex word
   extraction, stopwords removed).
2. Score = `(overlap × 100) + (tag_matches × 25) + type_weight`, where `overlap` is the
   size of the set intersection between query tokens and the memory's own tokens.
3. If the query has meaningful tokens and a candidate has neither lexical overlap nor an
   explicit tag match, it's excluded entirely — not merely ranked low.
4. Recency is a secondary tie-breaker.
5. Results are capped at `MAX_RETRIEVED_MEMORIES = 5`.

There is no embedding-based or cosine-similarity search anywhere in this module — a query
about "revenue" will only surface memories whose own text or tags share that vocabulary,
not memories that are conceptually related but phrased differently.

## Compaction

Memory records are not compacted, merged, or summarized. Each write is its own discrete
row; nothing prunes, deduplicates, or rewrites older memories as new ones accumulate. The
"compaction" concept in this system belongs to the runtime's per-run observation window
(see [conversations-and-runs.md](conversations-and-runs.md#compaction)), not to memory.

## Persistence and tenant scope

Memory is workspace-scoped (`memories.workspace_id`) and, unlike traces, genuinely durable
when `MEMORY_BACKEND=postgres` — the default `in_memory` backend loses all memory on
process restart, same trade-off as `ARTIFACT_BACKEND`/`IDENTITY_BACKEND`/`TENANCY_BACKEND`
(see [configuration.md](../getting-started/configuration.md)). `run_id`/`session_id`
columns on a memory record are loose correlation strings, not foreign keys — a memory can
outlive the run or session that created it by design.

## Known limitations

- No semantic/vector retrieval — relevance depends on shared vocabulary between the query
  and the stored content or tags.
- No memory consolidation or forgetting mechanism — memories accumulate indefinitely
  unless deleted by some other process; this document found no automatic pruning.
