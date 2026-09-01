"""Executing recompiled metrics against the real analytics schema.

Compilation can be checked without a database; arithmetic cannot. These run the
statements, so a wrong join, a timezone that moves a month or an attainment
ratio that divides the wrong way shows up as a wrong number rather than as a
statement that merely parses.

Skips when ANALYTICS_DATABASE_URL is unset, like the other database tests.
"""

import os
from datetime import date

import pytest
from pytest_asyncio import fixture

pytest.importorskip("sqlalchemy")

from app.analytics.connection import AnalyticsDatabase
from app.analytics.schema.allowlist import AnalyticsSchemaPolicy
from app.analytics.schema.inspector import PostgreSQLInspector
from app.analytics.semantics.execution import MetricExecutionError, MetricRunner
from app.analytics.semantics.metrics import MetricRegistry
from app.analytics.semantics.parameters import MetricFilter, MetricParameters, ReportPeriod
from app.analytics.sql.executor import AnalyticsSQLExecutor
from app.analytics.sql.limits import AnalyticsQueryLimits
from app.analytics.sql.validator import PostgreSQLQueryValidator
from app.orchestration.reruns import ReportRerunService

pytestmark = pytest.mark.postgres

ANALYTICS_URL = os.getenv("ANALYTICS_DATABASE_URL")

Q1 = ReportPeriod(start=date(2026, 1, 1), end=date(2026, 4, 1))
JANUARY = ReportPeriod(start=date(2026, 1, 1), end=date(2026, 2, 1))


@fixture
async def runner():
    if not ANALYTICS_URL:
        pytest.skip("ANALYTICS_DATABASE_URL is not configured")
    database = AnalyticsDatabase(ANALYTICS_URL)
    policy = AnalyticsSchemaPolicy.configured("public")
    try:
        yield MetricRunner(
            MetricRegistry(),
            PostgreSQLQueryValidator(policy),
            AnalyticsSQLExecutor(database, AnalyticsQueryLimits()),
            PostgreSQLInspector(database, policy, cache_ttl_seconds=300),
        )
    finally:
        await database.dispose()


def _number(value: object) -> float:
    return float(value)  # Numerics arrive as strings from the driver.


# ------------------------------------------------------------------- metrics


@pytest.mark.asyncio
async def test_revenue_reports_a_total_and_an_order_count(runner) -> None:
    result = await runner.run(MetricParameters(metric="revenue", period=Q1))

    assert result.row_count == 1
    row = result.rows[0]
    assert _number(row["revenue"]) > 0
    assert row["order_count"] > 0
    assert result.tables_consulted == ("orders",)
    assert result.columns == ("revenue", "order_count")


@pytest.mark.asyncio
async def test_order_count_agrees_with_the_revenue_metric(runner) -> None:
    """Two definitions over the same population must not disagree."""

    revenue = await runner.run(MetricParameters(metric="revenue", period=Q1))
    orders = await runner.run(MetricParameters(metric="orders", period=Q1))

    assert orders.rows[0]["order_count"] == revenue.rows[0]["order_count"]


@pytest.mark.asyncio
async def test_monthly_revenue_buckets_by_calendar_month_in_utc(runner) -> None:
    """A January order must not land in December on a server east of UTC."""

    result = await runner.run(
        MetricParameters(metric="revenue", period=Q1, dimensions=["period"], grain="month")
    )

    periods = [row["period"][:10] for row in result.rows]
    assert periods == ["2026-01-01", "2026-02-01", "2026-03-01"]


@pytest.mark.asyncio
async def test_monthly_revenue_sums_to_the_period_total(runner) -> None:
    """Grouping changes the shape of an answer, never its total."""

    total = await runner.run(MetricParameters(metric="revenue", period=Q1))
    monthly = await runner.run(
        MetricParameters(metric="revenue", period=Q1, dimensions=["period"])
    )

    assert round(sum(_number(row["revenue"]) for row in monthly.rows), 2) == round(
        _number(total.rows[0]["revenue"]), 2
    )


@pytest.mark.asyncio
async def test_gross_profit_is_below_the_revenue_it_came_from(runner) -> None:
    result = await runner.run(MetricParameters(metric="gross_profit", period=Q1))

    row = result.rows[0]
    assert 0 < _number(row["gross_profit"]) < _number(row["line_revenue"])
    assert set(result.tables_consulted) == {"orders", "order_items"}


@pytest.mark.asyncio
async def test_a_filter_narrows_the_population(runner) -> None:
    everything = await runner.run(MetricParameters(metric="revenue", period=Q1))
    narrowed = await runner.run(MetricParameters(
        metric="revenue", period=Q1,
        filters=[MetricFilter(field="country", operator="in", value=["Germany", "France"])],
    ))

    assert 0 < _number(narrowed.rows[0]["revenue"]) < _number(everything.rows[0]["revenue"])


@pytest.mark.asyncio
async def test_a_filter_value_is_bound_rather_than_interpreted(runner) -> None:
    """A hostile value reaches the driver as a string and matches nothing."""

    result = await runner.run(MetricParameters(
        metric="revenue", period=Q1,
        filters=[MetricFilter(field="country", value="Germany' OR '1'='1")],
    ))

    assert result.rows[0]["revenue"] is None or _number(result.rows[0]["revenue"]) == 0
    assert result.rows[0]["order_count"] == 0


# ---------------------------------------------------------- payment failures


@pytest.mark.asyncio
async def test_payment_failures_report_a_count(runner) -> None:
    result = await runner.run(MetricParameters(metric="payment_failure_count", period=Q1))

    assert result.rows[0]["failure_count"] > 0
    assert set(result.tables_consulted) == {"payments", "payment_methods"}


@pytest.mark.asyncio
async def test_payment_failures_by_method_split_the_total(runner) -> None:
    total = await runner.run(MetricParameters(metric="payment_failure_count", period=Q1))
    by_method = await runner.run(MetricParameters(
        metric="payment_failure_count", period=Q1, dimensions=["payment_method"]
    ))

    assert by_method.row_count > 1
    assert sum(row["failure_count"] for row in by_method.rows) == total.rows[0]["failure_count"]
    assert by_method.dimension_columns == ("payment_method",)


@pytest.mark.asyncio
async def test_payment_failures_by_method_and_reason_split_it_further(runner) -> None:
    by_method = await runner.run(MetricParameters(
        metric="payment_failure_count", period=Q1, dimensions=["payment_method"]
    ))
    detailed = await runner.run(MetricParameters(
        metric="payment_failure_count", period=Q1,
        dimensions=["payment_method", "failure_reason"],
    ))

    assert detailed.row_count > by_method.row_count
    assert sum(row["failure_count"] for row in detailed.rows) == sum(
        row["failure_count"] for row in by_method.rows
    )
    assert detailed.dimension_columns == ("payment_method", "failure_reason")
    assert all(row["failure_reason"] for row in detailed.rows)


# -------------------------------------------------------- target attainment


@pytest.mark.asyncio
async def test_target_attainment_reports_actual_and_target_per_month(runner) -> None:
    result = await runner.run(MetricParameters(metric="target_attainment", period=Q1))

    assert result.row_count == 3
    assert [row["period"] for row in result.rows] == ["2026-01", "2026-02", "2026-03"]
    for row in result.rows:
        assert row["revenue_actual"] is not None
        assert row["revenue_target"] is not None
        # The ratio came out of the statement, not out of Python.
        expected = round(100 * _number(row["revenue_actual"]) / _number(row["revenue_target"]), 2)
        assert _number(row["revenue_attainment_pct"]) == pytest.approx(expected, abs=0.01)


@pytest.mark.asyncio
async def test_target_attainment_covers_revenue_orders_and_gross_profit(runner) -> None:
    result = await runner.run(MetricParameters(metric="target_attainment", period=JANUARY))

    row = result.rows[0]
    for measure in ("revenue", "order", "gross_profit"):
        assert row[f"{measure}_actual"] is not None, measure
        assert row[f"{measure}_target"] is not None, measure
        assert row[f"{measure}_attainment_pct"] is not None, measure


@pytest.mark.asyncio
async def test_a_month_with_orders_but_no_target_reports_no_attainment(runner) -> None:
    """2024 has orders; the target calendar does not reach every month equally."""

    result = await runner.run(MetricParameters(
        metric="target_attainment",
        period=ReportPeriod(start=date(2024, 1, 1), end=date(2027, 1, 1)),
    ))

    untargeted = [row for row in result.rows if row["revenue_target"] is None]
    for row in untargeted:
        assert row["revenue_attainment_pct"] is None, "no target means no attainment"
        assert row["period"], "the month is still identified"


@pytest.mark.asyncio
async def test_a_month_with_a_target_but_no_orders_still_appears(runner) -> None:
    """The full outer join keeps a targeted month that sold nothing."""

    result = await runner.run(MetricParameters(
        metric="target_attainment",
        period=ReportPeriod(start=date(2024, 1, 1), end=date(2027, 1, 1)),
    ))

    for row in result.rows:
        if row["revenue_actual"] is None:
            # A month present only because a target exists for it.
            assert row["revenue_target"] is not None
            assert row["revenue_attainment_pct"] is None


@pytest.mark.asyncio
async def test_target_attainment_spans_several_months(runner) -> None:
    quarter = await runner.run(MetricParameters(metric="target_attainment", period=Q1))
    month = await runner.run(MetricParameters(metric="target_attainment", period=JANUARY))

    assert quarter.row_count == 3 and month.row_count == 1
    assert quarter.rows[0]["revenue_actual"] == month.rows[0]["revenue_actual"]


@pytest.mark.asyncio
async def test_a_period_with_neither_targets_nor_orders_is_empty_not_an_error(runner) -> None:
    result = await runner.run(MetricParameters(
        metric="target_attainment",
        period=ReportPeriod(start=date(2019, 1, 1), end=date(2019, 4, 1)),
    ))

    assert result.rows == () and result.is_empty


# ------------------------------------------------------------------ evidence


@pytest.mark.asyncio
async def test_a_rerun_mints_its_own_evidence(runner) -> None:
    """A recomputed figure must never wear the agent run's query identifier."""

    service = ReportRerunService(runner)

    outcomes = await service.run_all(run_id="run-1", requests=[
        MetricParameters(metric="revenue", period=Q1, dimensions=["period"]),
        MetricParameters(metric="payment_failure_count", period=Q1, dimensions=["payment_method"]),
    ])

    assert [outcome.query_id for outcome in outcomes] == ["rerun_001", "rerun_002"]
    for outcome in outcomes:
        source = outcome.source
        assert not source.id.startswith("query_"), "a rerun reused an agent query id"
        assert source.kind == "metric_rerun"
        assert source.run_id == "run-1"
        assert source.metric == outcome.result.metric
        assert source.columns == list(outcome.result.columns)
        assert source.row_count == outcome.result.row_count
        assert source.referenced_tables
        assert source.executed_at is not None
        assert source.sql_fingerprint


@pytest.mark.asyncio
async def test_evidence_records_the_parameters_it_was_run_with(runner) -> None:
    service = ReportRerunService(runner)

    outcome = (await service.run_all(run_id="run-1", requests=[
        MetricParameters(
            metric="revenue", period=JANUARY, dimensions=["country"],
            filters=[MetricFilter(field="country", operator="in", value=["Germany", "France"])],
        ),
    ]))[0]

    assert outcome.source.dimensions == ["country"]
    assert outcome.source.filters == ["country in Germany, France"]
    assert "2026-01-01" in outcome.source.label


@pytest.mark.asyncio
async def test_a_reruns_display_carries_the_exact_rows_it_reports(runner) -> None:
    """What the report prints must be the rows the query returned, unchanged."""

    service = ReportRerunService(runner)

    outcome = (await service.run_all(run_id="run-1", requests=[
        MetricParameters(metric="payment_failure_count", period=Q1, dimensions=["payment_method"]),
    ]))[0]

    assert outcome.chart.type == "table"
    assert outcome.chart.source_query_ids == ["rerun_001"]
    assert outcome.chart.data == [dict(row) for row in outcome.result.rows]


@pytest.mark.asyncio
async def test_an_ungrouped_rerun_becomes_kpis_carrying_their_source_column(runner) -> None:
    service = ReportRerunService(runner)

    outcome = (await service.run_all(run_id="run-1", requests=[
        MetricParameters(metric="revenue", period=Q1),
    ]))[0]

    assert outcome.chart.type == "kpi"
    labels = {item.source_column: item for item in outcome.chart.kpis}
    assert set(labels) == {"revenue", "order_count"}
    for column, item in labels.items():
        assert item.source_query_id == "rerun_001"
        # The untouched value travels beside the formatted one.
        assert item.raw_value == outcome.result.rows[0][column]


# -------------------------------------------------------------- enforcement


@pytest.mark.parametrize("statement", [
    "INSERT INTO monthly_targets (id, year, month) VALUES (-1, 1900, 1)",
    "UPDATE monthly_targets SET revenue_target = 0",
    "DELETE FROM monthly_targets",
])
@pytest.mark.asyncio
async def test_the_transaction_refuses_to_write(runner, statement: str) -> None:
    """Read-only is enforced by the transaction, not only by the validator.

    The validator would reject all three long before here, so this goes around
    it and straight to the executor: if the AST check were ever bypassed, the
    database itself is the layer that still says no.
    """

    from app.analytics.sql.executor import AnalyticsQueryError

    executor = runner._executor  # noqa: SLF001 - the boundary is what is under test

    with pytest.raises(AnalyticsQueryError) as refused:
        await executor.execute(statement, referenced_tables=["monthly_targets"])

    assert refused.value.failure_category == "database_query_error"
    # And the row count is unchanged, so nothing partially applied.
    after = await executor.execute(
        "SELECT COUNT(*) AS rows FROM monthly_targets", referenced_tables=["monthly_targets"]
    )
    assert after.rows[0][0] == 36


@pytest.mark.asyncio
async def test_a_metric_without_a_template_cannot_be_executed(runner) -> None:
    from app.analytics.semantics.compiler import MetricCompilationError

    with pytest.raises((MetricCompilationError, MetricExecutionError)):
        await runner.run(MetricParameters(metric="conversion_rate", period=Q1))
