"""The queries a run actually executed, as an answer can cite them.

Chart provenance is validated against the dataset store, which only holds
results small enough for Python analysis. That is the wrong ledger for
citations: a query returning more rows than the dataset limit is still evidence,
and refusing to cite it would block exactly the broad queries an aggregate rests
on. The trace records every query that completed, whatever its size, so the
trace is the ledger.
"""

from app.contracts.answers import AnswerSource
from app.observability.events import RunTrace, TraceEventType

_MAX_LABEL_TABLES = 3


def query_ledger(trace: RunTrace | None) -> dict[str, AnswerSource]:
    """Return every citable query of one run, keyed by its stable identifier."""

    if trace is None:
        return {}
    ledger: dict[str, AnswerSource] = {}
    for event in trace.events:
        if event.event_type is not TraceEventType.DATABASE_QUERY_FINISHED:
            continue
        query_id = event.metadata.get("query_id")
        if not isinstance(query_id, str) or not query_id:
            continue
        tables = [name for name in event.metadata.get("referenced_tables", []) if isinstance(name, str)]
        columns = [name for name in event.metadata.get("columns", []) if isinstance(name, str)]
        row_count = event.metadata.get("row_count")
        ledger[query_id] = AnswerSource(
            id=query_id,
            kind="database_query",
            run_id=trace.run_id,
            label=_label(query_id, event.metadata.get("purpose"), tables),
            referenced_tables=tables[:16],
            columns=columns[:32],
            row_count=row_count if isinstance(row_count, int) else None,
            truncated=bool(event.metadata.get("truncated", False)),
            executed_at=event.timestamp,
        )
    return ledger


def resolve_citations(
    trace: RunTrace | None, citations: list[str]
) -> tuple[list[AnswerSource], list[str]]:
    """Split cited identifiers into resolved sources and unresolvable references.

    Order follows the answer's citations so the registry reads the way the
    answer does, and a repeated citation contributes one source.
    """

    ledger = query_ledger(trace)
    resolved: list[AnswerSource] = []
    unresolved: list[str] = []
    seen: set[str] = set()
    for citation in citations:
        if not isinstance(citation, str) or citation in seen:
            continue
        seen.add(citation)
        source = ledger.get(citation)
        if source is None:
            unresolved.append(citation)
        else:
            resolved.append(source)
    return resolved, unresolved


def _label(query_id: str, purpose: object, tables: list[str]) -> str:
    """Name the evidence the way a reader would, falling back to what it read."""

    if isinstance(purpose, str) and purpose.strip():
        return purpose.strip()[:200]
    if tables:
        listed = ", ".join(tables[:_MAX_LABEL_TABLES])
        suffix = f" +{len(tables) - _MAX_LABEL_TABLES}" if len(tables) > _MAX_LABEL_TABLES else ""
        return f"Query on {listed}{suffix}"[:200]
    return f"Query {query_id}"
