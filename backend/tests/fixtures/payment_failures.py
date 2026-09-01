"""One completed investigation, fixed in place so CI never needs a model.

The acceptance scenario is "Show payment failures by payment method and failure
reason for 2026". This module is what such a run leaves behind: a written
answer, the displays it produced, the limitations it stated, and — built from a
real trace rather than written by hand — the evidence its citations resolve to.

Deriving the sources from a trace matters. It is how the runtime actually mints
them, so a fixture that skipped that step would prove the report renders while
saying nothing about whether provenance survives the journey. The citation list
below deliberately includes one identifier the run never executed, so every test
built on this fixture also demonstrates that unknown citations are dropped.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.analytics.presentation.charts import ChartSpec
from app.observability import TraceEventType, TraceRecorder
from app.observability.evidence import resolve_citations
from app.observability.in_memory import InMemoryTraceStore

RUN_ID = "run-payment-failures-2026"
PERIOD = "2026"

#: What the analyst wrote. Prose only — every number in it also appears in a
#: display, which is what makes the citations checkable.
ANSWER = """## Payment failures concentrated in two methods

Payment failures totalled 10,732 attempts across 2026, worth $23.4M in
attempted value. Card rails account for most of them.

- Visa and Mastercard together carry 58% of all failures.
- `technical_error` is the largest single reason at 3,822 attempts.
- Wallet methods fail least often in absolute terms.

Failure reasons differ by method rather than being uniform, so a single
remediation is unlikely to address all of them.
"""

#: Stated by the run about its own findings.
CAVEATS = [
    "Counts are payment attempts, not distinct orders; one order may fail several times.",
    "Failure reasons are supplied by the payment provider and are not independently verified.",
    "December 2026 is incomplete in the source data, so the annual total is a lower bound.",
]

#: What the answer cites. `query_009` was never executed by this run — it is here
#: so that dropping unknown citations is exercised rather than assumed.
CITATIONS = ["query_001", "query_002", "query_003", "query_009"]

#: The queries the run actually ran, as the trace recorded them.
EXECUTED_QUERIES = [
    {
        "query_id": "query_001",
        "purpose": "Total payment failures and attempted value for 2026",
        "referenced_tables": ["payments"],
        "columns": ["failure_count", "failed_amount"],
        "row_count": 1,
    },
    {
        "query_id": "query_002",
        "purpose": "Payment failures by method and failure reason for 2026",
        "referenced_tables": ["payments", "payment_methods"],
        "columns": ["payment_method", "failure_reason", "failure_count"],
        "row_count": 15,
    },
    {
        "query_id": "query_003",
        "purpose": "Payment failures by method with attempted value for 2026",
        "referenced_tables": ["payments", "payment_methods"],
        "columns": ["payment_method", "failure_count", "failed_amount"],
        "row_count": 5,
    },
]

#: The rows behind the stacked bar. Long form — one row per method and reason —
#: which is the shape the Workbench renderer and the Matplotlib exporter both
#: pivot into one series per reason.
FAILURE_BREAKDOWN = [
    {"payment_method": method, "failure_reason": reason, "failure_count": count}
    for method, reasons in {
        "visa": {"technical_error": 1204, "insufficient_funds": 1098, "bank_declined": 1062},
        "mastercard": {"technical_error": 1010, "insufficient_funds": 921, "bank_declined": 889},
        "paypal": {"technical_error": 702, "insufficient_funds": 640, "bank_declined": 611},
        "apple_pay": {"technical_error": 512, "insufficient_funds": 468, "bank_declined": 447},
        "bank_transfer": {"technical_error": 394, "insufficient_funds": 372, "bank_declined": 402},
    }.items()
    for reason, count in reasons.items()
]

#: The supporting table: one row per method, with attempted value.
METHOD_TOTALS = [
    {"payment_method": "visa", "failure_count": 3364, "failed_amount": 7412883.41},
    {"payment_method": "mastercard", "failure_count": 2820, "failed_amount": 6155201.08},
    {"payment_method": "paypal", "failure_count": 1953, "failed_amount": 4268117.92},
    {"payment_method": "apple_pay", "failure_count": 1427, "failed_amount": 3104556.30},
    {"payment_method": "bank_transfer", "failure_count": 1168, "failed_amount": 2503994.77},
]


def chart_specs() -> list[ChartSpec]:
    """The displays the run produced: a KPI card, a stacked bar and a table."""

    return [
        ChartSpec(
            id="kpi-failures", type="kpi", title="Payment failures, 2026",
            source_query_ids=["query_001"],
            kpis=[
                {"label": "Failed attempts", "value": "10,732", "raw_value": 10732,
                 "source_column": "failure_count", "source_query_id": "query_001",
                 "row_selector": {"period": "2026"}},
                {"label": "Attempted value", "value": "$23.4M", "raw_value": 23444753.48,
                 "source_column": "failed_amount", "source_query_id": "query_001",
                 "row_selector": {"period": "2026"}},
            ],
        ),
        ChartSpec(
            id="failures-by-method-reason", type="stacked_bar",
            title="Payment failures by method and reason",
            description="Attempts that failed in 2026, stacked by the reason the provider gave.",
            x_field="payment_method", y_fields=["failure_count"],
            data=FAILURE_BREAKDOWN, source_query_ids=["query_002"],
        ),
        ChartSpec(
            id="failures-by-method", type="table",
            title="Failures and attempted value by method",
            data=METHOD_TOTALS, source_query_ids=["query_003"],
        ),
    ]


def answer_sources():
    """Resolve the answer's citations against a trace of what actually ran.

    Returns the resolved sources and the citations that could not be accounted
    for, so a caller can assert on both halves.
    """

    recorder = TraceRecorder(InMemoryTraceStore())
    recorder.start_run(run_id=RUN_ID, parent_run_id=None, agent_name="data_analyst",
                       agent_type="specialist", goal="Payment failures for 2026")
    for index, query in enumerate(EXECUTED_QUERIES):
        # Numbering follows the validation events, exactly as the observers do.
        recorder.record(RUN_ID, TraceEventType.DATABASE_QUERY_VALIDATION_STARTED,
                        iteration=index + 1, metadata={"query_id": query["query_id"]})
        recorder.record(
            RUN_ID, TraceEventType.DATABASE_QUERY_FINISHED, iteration=index + 1,
            duration_ms=40 + index * 7, success=True,
            metadata={
                "query_id": query["query_id"], "purpose": query["purpose"],
                "referenced_tables": query["referenced_tables"],
                "columns": query["columns"], "row_count": query["row_count"],
                "truncated": False,
            },
        )
    return resolve_citations(recorder.get_trace(RUN_ID), CITATIONS)


def completed_run():
    """The persisted run a publisher reads, shaped like an ``AgentRunRecord``."""

    resolved, _ = answer_sources()
    return SimpleNamespace(
        id=RUN_ID, status="completed", created_at=datetime.now(UTC),
        chart_specs=[chart.model_dump(mode="json") for chart in chart_specs()],
        answer_sources=[source.model_dump(mode="json") for source in resolved],
        answer_caveats=list(CAVEATS),
    )


def conversation_store():
    """A store returning the completed run, without a database behind it."""

    async def value(item):
        return item

    run = completed_run()
    return SimpleNamespace(
        get_run=lambda run_id: value(run),
        get_assistant_message_for_run=lambda run_id: value(SimpleNamespace(content=ANSWER)),
    )
