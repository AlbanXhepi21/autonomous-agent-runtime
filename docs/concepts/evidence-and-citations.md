# Evidence and citations

> **A citation confirms that the referenced query executed. It does not independently
> prove that every narrative claim was mathematically derived from that query.**

Everything in this document exists to make that sentence precise: what a citation actually
guarantees, what creates one, and — just as importantly — what it does not guarantee. See
also [security-boundaries.md](../architecture/security-boundaries.md#evidence-resolution)
for how an unresolved citation is handled as a trust-boundary question.

## Creation of `query_###`

A `query_id` is **not** a UUID. It's a run-scoped, 1-indexed, zero-padded sequential
counter, minted the moment a `query_database` call is traced:

```python
# backend/app/tools/execution/observers.py — _query_run_context
seen = sum(
    1 for event in (trace.events if trace else [])
    if event.event_type is TraceEventType.DATABASE_QUERY_VALIDATION_STARTED
)
return {"query_id": f"query_{seen + 1:03d}"}
```

It counts `DATABASE_QUERY_VALIDATION_STARTED` events already recorded in *this run's*
trace, so the first query in a run is always `query_001`, the second `query_002`, and so
on — the numbering has no meaning outside the run it belongs to. The ID is threaded back
into the tool's own output, and `analyze_dataset`'s dataset ID is derived from it
(`dataset_{query_id}`).

## Creation of rerun evidence

A parameterized report rerun (see [reporting.md](../architecture/reporting.md#parameterized-reruns))
produces evidence in a **separate identifier namespace**, deliberately distinct from
`query_###` so a recomputed figure can never be mistaken for evidence a live agent run
actually produced:

```python
# backend/app/orchestration/reruns.py
RERUN_PREFIX = "rerun"
def rerun_query_id(index: int) -> str:
    return f"{RERUN_PREFIX}_{index:03d}"
```

Numbered 1-indexed per report, capped at 8 reruns per report. The resulting `AnswerSource`
carries `kind="metric_rerun"` (versus `"database_query"` for a live run) and — only in
this case — populates `metric`, `dimensions`, `filters`, and `sql_fingerprint`, fields a
live query's source never sets. The module's own reasoning: a rerun is "a compilation and
an execution" against a governed, pre-validated metric definition — "no part of it is
authored by a model" — which is a genuinely different provenance story from agent-written
SQL, even though both are represented through the same `AnswerSource` type.

## The trace-derived ledger

`query_ledger()` (`backend/app/observability/evidence.py`) builds a
`dict[query_id, AnswerSource]` by reading exactly one trace event type:
`TraceEventType.DATABASE_QUERY_FINISHED`. No other event type contributes to the ledger.
From each such event's metadata it extracts: `query_id` (becomes the source's own ID —
skipped if missing), `referenced_tables` (capped at 16), `columns` (capped at 32),
`row_count`, `truncated`, and the event's timestamp as `executed_at`. A label is derived
from the model's stated `purpose` argument if present, else a generated
`"Query on {tables}"` string, else `"Query {query_id}"`.

## Citation resolution

`resolve_citations(trace, citations)` matches each citation string against the ledger by
**exact key lookup** — a citation must equal a `query_id` character-for-character. It
returns a `(resolved, unresolved)` pair:

- Matched citations become `AnswerSource` objects in `resolved`.
- Duplicate citations (already seen) are silently skipped, preserving first-appearance
  order.
- A citation with no match in the ledger goes into `unresolved` as the bare string — it is
  **neither dropped without a trace, nor kept as if it were valid evidence.**

## Unknown-citation removal

An unresolved citation does not block the run or the answer — it's logged as a structured
`answer_citation_unresolved` event with the unresolved list attached, and it simply does
not appear in the answer's attached evidence. This review did not find code that surfaces
the unresolved list itself into the published report or the end-user-visible answer — only
into the logs. Practically: a citation to a query that never ran, or was mistyped, is
caught and excluded from the evidence actually shown, rather than trusted at face value.

## Evidence persistence

Only a **completed** run's evidence is persisted. `AgentRunManager` reduces
`answer_sources`/`answer_caveats` to `None` for any non-`"completed"` terminal status; for
a completed run, the full `AnswerSource` objects are serialized (`model_dump(mode="json")`)
and written onto the `AgentRunRecord.answer_sources`/`answer_caveats` JSONB columns via
`ConversationStore.finish_run`. This is a deliberate denormalization: the trace the
citations were originally resolved against is process-local and does not survive a
restart (see [conversations-and-runs.md](conversations-and-runs.md#trace-events)), so the
snapshot on the run record is the only thing that outlives the process.

## Evidence appendix

A published report's `evidence` block (see
[reporting.md](../architecture/reporting.md#evidence-appendix)) renders one entry per
cited query — its description, when it ran, tables/columns touched, row count, and
truncation flag — sourced from the same `AnswerSource` objects, whether from a live run's
ledger or a rerun's `_source_for`.

## Exact displayed-row provenance

Each evidence entry also carries `displayed_rows: dict[figure_label, CompiledRows]` — a
literal reference to the **same rows a chart or table block was already built with**, not
a recomputation. The report compiler walks every block, and for each `query_id` a block
cites, records that block's own `data` under the block's figure label:

```python
for query_id in block.source_query_ids or ():
    if label:
        used_by.setdefault(query_id, []).append(label)
        displayed.setdefault(query_id, {})[label] = block.data
```

So an evidence entry's `displayed_rows["Revenue by Region"]`, for example, is exactly the
rows that chart was rendered from — not a fresh query, not an approximation.

## Verified factual claims: no such mechanism exists beyond citation resolution

This documentation set searched the codebase for anything resembling a stronger
guarantee than citation resolution — fact-checking, claim verification, a
"mathematically derived" or provenance-tier distinction — and found **none**. There is no
`verified_fact`, `fact_check`, or `provenance_level` concept anywhere in the backend. The
closest adjacent ideas are:

- The investigation plan's evidence-ID reconciliation (see
  [agent-runtime.md](../architecture/agent-runtime.md#investigation-planning)), which
  checks that a plan item's claimed evidence IDs exist in the query ledger — this is the
  *same* citation-resolution mechanism applied to plan bookkeeping, not a separate
  verification layer.
- The `metric_rerun` source kind, which does carry a different (arguably stronger)
  provenance story — compiled from a governed, pre-validated metric definition rather than
  agent-authored SQL — but it is represented as just another value of `AnswerSourceKind`,
  not a "verified" flag or a distinct pipeline the reader can rely on differently.

In short: **a citation resolving successfully means the named query executed and its
metadata is on record — it says nothing about whether the sentence citing it is an
accurate summary of that query's result.** No mechanism in this codebase checks the latter.
