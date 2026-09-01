"""What an answer is allowed to cite, and what a citation carries once stored."""

from app.observability import TraceEventType, TraceRecorder, query_ledger, resolve_citations
from app.observability.in_memory import InMemoryTraceStore


def _recorder_with_queries(*queries: dict[str, object]) -> TraceRecorder:
    recorder = TraceRecorder(InMemoryTraceStore())
    recorder.start_run(run_id="run-1", parent_run_id=None, agent_name="data_analyst",
                       agent_type="specialist", goal="Why did revenue fall?")
    for query in queries:
        recorder.record("run-1", TraceEventType.DATABASE_QUERY_FINISHED, metadata=query)
    return recorder


def test_every_completed_query_is_citable_whatever_its_size() -> None:
    # The dataset store drops results too large for Python analysis. Citations
    # are validated against the trace instead, so a broad aggregate query is
    # still admissible evidence.
    recorder = _recorder_with_queries(
        {"query_id": "query_001", "referenced_tables": ["orders"], "row_count": 50_000,
         "truncated": True, "purpose": "Order volume by month"},
    )

    ledger = query_ledger(recorder.get_trace("run-1"))

    assert ledger["query_001"].row_count == 50_000
    assert ledger["query_001"].truncated is True


def test_a_citation_carries_what_it_needs_to_outlive_its_trace() -> None:
    recorder = _recorder_with_queries(
        {"query_id": "query_003", "referenced_tables": ["orders", "order_items"],
         "row_count": 12, "truncated": False, "purpose": "Revenue by category"},
    )

    source = query_ledger(recorder.get_trace("run-1"))["query_003"]

    assert source.id == "query_003"
    assert source.run_id == "run-1"
    assert source.kind == "database_query"
    assert source.label == "Revenue by category"
    assert source.referenced_tables == ["orders", "order_items"]
    assert source.executed_at is not None


def test_a_query_without_a_purpose_is_labelled_by_what_it_read() -> None:
    recorder = _recorder_with_queries(
        {"query_id": "query_001", "referenced_tables": ["orders", "customers"], "row_count": 4},
    )

    assert query_ledger(recorder.get_trace("run-1"))["query_001"].label == (
        "Query on orders, customers"
    )


def test_uncited_evidence_stays_out_of_the_registry() -> None:
    recorder = _recorder_with_queries(
        {"query_id": "query_001", "referenced_tables": ["orders"], "row_count": 1},
        {"query_id": "query_002", "referenced_tables": ["customers"], "row_count": 1},
    )

    resolved, unresolved = resolve_citations(recorder.get_trace("run-1"), ["query_002"])

    assert [source.id for source in resolved] == ["query_002"]
    assert unresolved == []


def test_an_invented_reference_resolves_to_nothing() -> None:
    recorder = _recorder_with_queries({"query_id": "query_001", "row_count": 1})

    resolved, unresolved = resolve_citations(
        recorder.get_trace("run-1"), ["query_001", "query_009"]
    )

    assert [source.id for source in resolved] == ["query_001"]
    assert unresolved == ["query_009"]


def test_a_repeated_citation_contributes_one_source() -> None:
    recorder = _recorder_with_queries({"query_id": "query_001", "row_count": 1})

    resolved, _ = resolve_citations(recorder.get_trace("run-1"), ["query_001", "query_001"])

    assert len(resolved) == 1


def test_an_expired_trace_yields_no_sources_rather_than_failing() -> None:
    resolved, unresolved = resolve_citations(None, ["query_001"])

    assert resolved == []
    assert unresolved == ["query_001"]
