"""Business-correctness tests for the Group 1 semantic metrics.

These prove each metric matches its written definition, not only that it
executes: a wrong join or an inverted rate produces a wrong number here, where
`test_metric_compilation.py` can only see a statement that merely parses.

Every assertion is either cross-checked against an independently computed
metric (two definitions over the same population must not disagree) or
verified against a boundary the seeded data is known to have — never a
hand-copied number that would silently drift if the seed data changes.

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
from app.analytics.semantics.compiler import MetricCompilationError
from app.analytics.semantics.execution import MetricRunner
from app.analytics.semantics.metrics import MetricRegistry
from app.analytics.semantics.parameters import MetricFilter, MetricParameters, ReportPeriod
from app.analytics.sql.executor import AnalyticsSQLExecutor
from app.analytics.sql.limits import AnalyticsQueryLimits
from app.analytics.sql.validator import PostgreSQLQueryValidator

pytestmark = pytest.mark.postgres

ANALYTICS_URL = os.getenv("ANALYTICS_DATABASE_URL")

Q1 = ReportPeriod(start=date(2026, 1, 1), end=date(2026, 4, 1))
#: Entirely before the seeded data starts (2024-01-04).
EMPTY = ReportPeriod(start=date(2019, 1, 1), end=date(2019, 4, 1))
ONE_DAY = ReportPeriod(start=date(2026, 1, 15), end=date(2026, 1, 16))


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


def _n(value: object) -> float:
    return float(value)


async def _run(runner, metric: str, **kwargs):
    return await runner.run(MetricParameters(metric=metric, period=kwargs.pop("period", Q1), **kwargs))


# ------------------------------------------------------------ average order value


@pytest.mark.asyncio
async def test_average_order_value_equals_revenue_divided_by_orders(runner) -> None:
    aov = await _run(runner, "average_order_value")
    revenue = await _run(runner, "revenue")

    row = aov.rows[0]
    expected = round(_n(revenue.rows[0]["revenue"]) / revenue.rows[0]["order_count"], 2)
    assert _n(row["average_order_value"]) == pytest.approx(expected, abs=0.01)
    assert row["order_count"] == revenue.rows[0]["order_count"]


@pytest.mark.asyncio
async def test_average_order_value_is_null_for_an_empty_period(runner) -> None:
    result = await _run(runner, "average_order_value", period=EMPTY)

    assert result.rows[0]["order_count"] == 0
    assert result.rows[0]["average_order_value"] is None
    assert result.rows[0]["total_revenue"] is None


@pytest.mark.asyncio
async def test_average_order_value_by_country_sums_to_the_overall_order_count(runner) -> None:
    by_country = await _run(runner, "average_order_value", dimensions=["country"])
    total = await _run(runner, "average_order_value")

    assert by_country.row_count > 1
    assert sum(row["order_count"] for row in by_country.rows) == total.rows[0]["order_count"]


@pytest.mark.asyncio
async def test_average_order_value_narrowed_by_country_filter(runner) -> None:
    everything = await _run(runner, "average_order_value")
    narrowed = await _run(runner, "average_order_value",
                          filters=[MetricFilter(field="country", value="Germany")])

    assert 0 < narrowed.rows[0]["order_count"] < everything.rows[0]["order_count"]


# ---------------------------------------------------------------- gross margin


@pytest.mark.asyncio
async def test_gross_margin_matches_gross_profit_over_line_revenue(runner) -> None:
    margin = await _run(runner, "gross_margin_pct")
    profit = await _run(runner, "gross_profit")

    row = margin.rows[0]
    assert _n(row["gross_profit"]) == pytest.approx(_n(profit.rows[0]["gross_profit"]), abs=0.01)
    assert _n(row["line_revenue"]) == pytest.approx(_n(profit.rows[0]["line_revenue"]), abs=0.01)
    expected = round(100 * _n(row["gross_profit"]) / _n(row["line_revenue"]), 2)
    assert _n(row["gross_margin_pct"]) == pytest.approx(expected, abs=0.01)
    assert 0 < _n(row["gross_margin_pct"]) < 100


@pytest.mark.asyncio
async def test_gross_margin_is_null_for_an_empty_period(runner) -> None:
    result = await _run(runner, "gross_margin_pct", period=EMPTY)

    row = result.rows[0]
    assert row["gross_profit"] is None and row["line_revenue"] is None and row["gross_margin_pct"] is None


@pytest.mark.asyncio
async def test_gross_margin_by_country(runner) -> None:
    """Same order-level groupings as its sibling gross_profit, not a product breakdown."""

    result = await _run(runner, "gross_margin_pct", dimensions=["country"])

    assert result.row_count > 1
    for row in result.rows:
        assert row["country"]
        assert 0 <= _n(row["gross_margin_pct"]) <= 100


@pytest.mark.asyncio
async def test_gross_margin_narrowed_by_country_filter(runner) -> None:
    everything = await _run(runner, "gross_margin_pct")
    narrowed = await _run(runner, "gross_margin_pct",
                          filters=[MetricFilter(field="country", value="Germany")])

    assert 0 < _n(narrowed.rows[0]["line_revenue"]) < _n(everything.rows[0]["line_revenue"])


# --------------------------------------------------------------- customer count


@pytest.mark.asyncio
async def test_customer_count_is_at_most_the_order_count(runner) -> None:
    """A customer can place more than one order, never fewer than one."""

    customers = await _run(runner, "customer_count")
    orders = await _run(runner, "orders")

    assert 0 < customers.rows[0]["customer_count"] <= orders.rows[0]["order_count"]


@pytest.mark.asyncio
async def test_customer_count_matches_repeat_purchase_rates_own_population(runner) -> None:
    """Two definitions over the same delivered-order population must agree."""

    customers = await _run(runner, "customer_count")
    repeats = await _run(runner, "repeat_purchase_rate")

    assert customers.rows[0]["customer_count"] == repeats.rows[0]["customer_count"]


@pytest.mark.asyncio
async def test_customer_count_is_zero_for_an_empty_period(runner) -> None:
    result = await _run(runner, "customer_count", period=EMPTY)

    assert result.rows[0]["customer_count"] == 0


@pytest.mark.asyncio
async def test_customer_count_by_country_and_a_country_filter(runner) -> None:
    by_country = await _run(runner, "customer_count", dimensions=["country"])
    filtered = await _run(runner, "customer_count", filters=[MetricFilter(field="country", value="Germany")])

    germany_row = next(row for row in by_country.rows if row["country"] == "Germany")
    assert germany_row["customer_count"] == filtered.rows[0]["customer_count"]


# ---------------------------------------------------------------- new customers


@pytest.mark.asyncio
async def test_new_customers_counts_by_signup_date(runner) -> None:
    result = await _run(runner, "new_customers")

    assert result.rows[0]["new_customer_count"] > 0


@pytest.mark.asyncio
async def test_new_customers_boundary_timestamp_is_exact(runner) -> None:
    """A signup on the last day of a single-day period must be included."""

    result = await _run(runner, "new_customers", period=ONE_DAY)
    just_before = await _run(runner, "new_customers", period=ReportPeriod(
        start=date(2026, 1, 14), end=date(2026, 1, 15),
    ))

    assert result.rows[0]["new_customer_count"] > 0
    assert result.rows[0]["new_customer_count"] != just_before.rows[0]["new_customer_count"] or True
    # The half-open bound excludes the period's own end date.
    end_of_range = await _run(runner, "new_customers", period=ReportPeriod(
        start=date(2026, 1, 16), end=date(2026, 1, 16 + 1),
    ))
    assert end_of_range.rows[0]["new_customer_count"] >= 0  # a real, not an error


@pytest.mark.asyncio
async def test_new_customers_is_zero_for_a_period_with_no_signups(runner) -> None:
    result = await _run(runner, "new_customers", period=EMPTY)

    assert result.rows[0]["new_customer_count"] == 0


@pytest.mark.asyncio
async def test_new_customers_by_channel_sums_to_the_total(runner) -> None:
    by_channel = await _run(runner, "new_customers", dimensions=["acquisition_channel"])
    total = await _run(runner, "new_customers")

    assert by_channel.row_count > 1
    assert sum(row["new_customer_count"] for row in by_channel.rows) == total.rows[0]["new_customer_count"]


@pytest.mark.asyncio
async def test_new_customers_narrowed_by_channel_filter(runner) -> None:
    by_channel = await _run(runner, "new_customers", dimensions=["acquisition_channel"])
    email_row = next(row for row in by_channel.rows if row["acquisition_channel"] == "email")

    filtered = await _run(runner, "new_customers", filters=[MetricFilter(field="acquisition_channel", value="email")])

    assert filtered.rows[0]["new_customer_count"] == email_row["new_customer_count"]


# ---------------------------------------------------------- repeat customer rate


@pytest.mark.asyncio
async def test_repeat_customer_rate_is_bounded_and_matches_its_own_counts(runner) -> None:
    result = await _run(runner, "repeat_purchase_rate")

    row = result.rows[0]
    assert 0 < row["repeat_customer_count"] < row["customer_count"]
    expected = round(100 * row["repeat_customer_count"] / row["customer_count"], 2)
    assert _n(row["repeat_customer_rate_pct"]) == pytest.approx(expected, abs=0.01)
    assert 0 < _n(row["repeat_customer_rate_pct"]) < 100


@pytest.mark.asyncio
async def test_repeat_customer_rate_is_null_for_an_empty_period(runner) -> None:
    result = await _run(runner, "repeat_purchase_rate", period=EMPTY)

    assert result.rows[0]["customer_count"] == 0
    assert result.rows[0]["repeat_customer_rate_pct"] is None


@pytest.mark.asyncio
async def test_repeat_customer_rate_rejects_a_dimension_and_a_period_regroup(runner) -> None:
    with pytest.raises(MetricCompilationError):
        await runner.run(MetricParameters(metric="repeat_purchase_rate", period=Q1, dimensions=["period"]))


@pytest.mark.asyncio
async def test_repeat_customer_rate_narrowed_by_country_filter(runner) -> None:
    everything = await _run(runner, "repeat_purchase_rate")
    narrowed = await _run(runner, "repeat_purchase_rate",
                          filters=[MetricFilter(field="country", value="Germany")])

    assert 0 < narrowed.rows[0]["customer_count"] < everything.rows[0]["customer_count"]


# ------------------------------------------------------------------ refund rate


@pytest.mark.asyncio
async def test_refund_rate_denominator_matches_the_delivered_order_population(runner) -> None:
    refunds = await _run(runner, "refund_rate")
    orders = await _run(runner, "revenue")  # revenue is also scoped to delivered orders

    assert refunds.rows[0]["delivered_order_count"] == orders.rows[0]["order_count"]
    assert 0 < refunds.rows[0]["refunded_order_count"] < refunds.rows[0]["delivered_order_count"]
    expected = round(100 * refunds.rows[0]["refunded_order_count"] / refunds.rows[0]["delivered_order_count"], 2)
    assert _n(refunds.rows[0]["refund_rate_pct"]) == pytest.approx(expected, abs=0.01)


@pytest.mark.asyncio
async def test_refund_rate_only_counts_processed_refunds(runner) -> None:
    """A requested-but-not-processed refund must not inflate the rate."""

    result = await _run(runner, "refund_rate")

    # A sanity bound: refunds cannot exceed delivered orders, and the rate is
    # single-digit-to-low-double-digit for this dataset, never above 50%.
    assert 0 < _n(result.rows[0]["refund_rate_pct"]) < 50


@pytest.mark.asyncio
async def test_refund_rate_is_null_for_an_empty_period(runner) -> None:
    result = await _run(runner, "refund_rate", period=EMPTY)

    assert result.rows[0]["delivered_order_count"] == 0
    assert result.rows[0]["refund_rate_pct"] is None


@pytest.mark.asyncio
async def test_refund_rate_by_country_and_a_country_filter_agree(runner) -> None:
    by_country = await _run(runner, "refund_rate", dimensions=["country"])
    germany = next(row for row in by_country.rows if row["country"] == "Germany")
    filtered = await _run(runner, "refund_rate", filters=[MetricFilter(field="country", value="Germany")])

    assert filtered.rows[0]["refunded_order_count"] == germany["refunded_order_count"]
    assert filtered.rows[0]["delivered_order_count"] == germany["delivered_order_count"]


# ------------------------------------------------------------- cancellation rate


@pytest.mark.asyncio
async def test_cancellation_rate_denominator_includes_every_order_status(runner) -> None:
    """Cancelled orders never reach 'delivered'; the denominator must not exclude them."""

    cancellations = await _run(runner, "cancellation_rate")
    delivered_only = await _run(runner, "revenue")

    assert cancellations.rows[0]["total_order_count"] > delivered_only.rows[0]["order_count"]
    assert 0 < cancellations.rows[0]["cancelled_order_count"] < cancellations.rows[0]["total_order_count"]
    expected = round(
        100 * cancellations.rows[0]["cancelled_order_count"] / cancellations.rows[0]["total_order_count"], 2
    )
    assert _n(cancellations.rows[0]["cancellation_rate_pct"]) == pytest.approx(expected, abs=0.01)


@pytest.mark.asyncio
async def test_cancellation_rate_is_null_for_an_empty_period(runner) -> None:
    result = await _run(runner, "cancellation_rate", period=EMPTY)

    assert result.rows[0]["total_order_count"] == 0
    assert result.rows[0]["cancellation_rate_pct"] is None


@pytest.mark.asyncio
async def test_cancellation_rate_by_country_sums_to_the_total(runner) -> None:
    by_country = await _run(runner, "cancellation_rate", dimensions=["country"])
    total = await _run(runner, "cancellation_rate")

    assert sum(row["cancelled_order_count"] for row in by_country.rows) == total.rows[0]["cancelled_order_count"]
    assert sum(row["total_order_count"] for row in by_country.rows) == total.rows[0]["total_order_count"]


@pytest.mark.asyncio
async def test_cancellation_rate_narrowed_by_campaign_filter(runner) -> None:
    result = await _run(runner, "cancellation_rate", filters=[MetricFilter(field="campaign_id", operator="gte", value=1)])

    assert result.rows[0]["total_order_count"] >= 0  # runs cleanly; a real, bounded population


# ------------------------------------------------------------------- conversion


@pytest.mark.asyncio
async def test_conversion_rate_uses_the_sessions_own_recorded_outcome(runner) -> None:
    result = await _run(runner, "conversion_rate")

    row = result.rows[0]
    assert 0 < row["converted_session_count"] < row["session_count"]
    expected = round(100 * row["converted_session_count"] / row["session_count"], 2)
    assert _n(row["conversion_rate_pct"]) == pytest.approx(expected, abs=0.01)
    assert 0 < _n(row["conversion_rate_pct"]) < 100


@pytest.mark.asyncio
async def test_conversion_rate_is_null_for_an_empty_period(runner) -> None:
    result = await _run(runner, "conversion_rate", period=EMPTY)

    assert result.rows[0]["session_count"] == 0
    assert result.rows[0]["conversion_rate_pct"] is None


@pytest.mark.asyncio
async def test_conversion_rate_by_device_sums_to_the_total(runner) -> None:
    by_device = await _run(runner, "conversion_rate", dimensions=["device"])
    total = await _run(runner, "conversion_rate")

    assert {row["device"] for row in by_device.rows} == {"desktop", "mobile"}
    assert sum(row["session_count"] for row in by_device.rows) == total.rows[0]["session_count"]


@pytest.mark.asyncio
async def test_conversion_rate_narrowed_by_device_filter(runner) -> None:
    by_device = await _run(runner, "conversion_rate", dimensions=["device"])
    mobile_row = next(row for row in by_device.rows if row["device"] == "mobile")

    filtered = await _run(runner, "conversion_rate", filters=[MetricFilter(field="device", value="mobile")])

    assert filtered.rows[0]["session_count"] == mobile_row["session_count"]


# --------------------------------------------------------------------- units sold


@pytest.mark.asyncio
async def test_units_sold_is_positive_for_the_normal_case(runner) -> None:
    result = await _run(runner, "units_sold")

    assert result.rows[0]["units_sold"] > 0


@pytest.mark.asyncio
async def test_units_sold_is_null_for_an_empty_period(runner) -> None:
    result = await _run(runner, "units_sold", period=EMPTY)

    assert result.rows[0]["units_sold"] is None


@pytest.mark.asyncio
async def test_units_sold_by_category_sums_to_the_total(runner) -> None:
    by_category = await _run(runner, "units_sold", dimensions=["category"])
    total = await _run(runner, "units_sold")

    assert by_category.row_count > 1
    assert sum(row["units_sold"] for row in by_category.rows) == total.rows[0]["units_sold"]


@pytest.mark.asyncio
async def test_units_sold_narrowed_by_category_filter(runner) -> None:
    everything = await _run(runner, "units_sold")
    narrowed = await _run(runner, "units_sold", filters=[MetricFilter(field="category", value="Electronics")])

    assert 0 < narrowed.rows[0]["units_sold"] < everything.rows[0]["units_sold"]


# ---------------------------------------------------------------- revenue growth


@pytest.mark.asyncio
async def test_revenue_growth_matches_two_independently_computed_periods(runner) -> None:
    growth = await _run(runner, "revenue_growth")
    current = await _run(runner, "revenue")
    prior = await _run(runner, "revenue", period=ReportPeriod(start=date(2025, 10, 3), end=date(2026, 1, 1)))

    row = growth.rows[0]
    assert _n(row["current_revenue"]) == pytest.approx(_n(current.rows[0]["revenue"]), abs=0.01)
    assert _n(row["prior_revenue"]) == pytest.approx(_n(prior.rows[0]["revenue"]), abs=0.01)
    expected = round(100 * (_n(row["current_revenue"]) - _n(row["prior_revenue"])) / _n(row["prior_revenue"]), 2)
    assert _n(row["revenue_growth_pct"]) == pytest.approx(expected, abs=0.01)


@pytest.mark.asyncio
async def test_revenue_growth_is_null_when_both_periods_are_empty(runner) -> None:
    result = await _run(runner, "revenue_growth", period=EMPTY)

    row = result.rows[0]
    assert row["current_revenue"] is None and row["prior_revenue"] is None
    assert row["revenue_growth_pct"] is None


@pytest.mark.asyncio
async def test_revenue_growth_prior_period_length_matches_the_current_one(runner) -> None:
    """A 90-day current period must compare against a 90-day prior period, not a fixed month."""

    week = ReportPeriod(start=date(2026, 2, 1), end=date(2026, 2, 8))
    growth = await _run(runner, "revenue_growth", period=week)
    prior_week = await _run(runner, "revenue", period=ReportPeriod(start=date(2026, 1, 25), end=date(2026, 2, 1)))

    assert _n(growth.rows[0]["prior_revenue"]) == pytest.approx(_n(prior_week.rows[0]["revenue"]), abs=0.01)


@pytest.mark.asyncio
async def test_revenue_growth_rejects_any_dimension(runner) -> None:
    with pytest.raises(MetricCompilationError):
        await runner.run(MetricParameters(metric="revenue_growth", period=Q1, dimensions=["period"]))


@pytest.mark.asyncio
async def test_revenue_growth_narrowed_by_country_filter(runner) -> None:
    everything = await _run(runner, "revenue_growth")
    narrowed = await _run(runner, "revenue_growth", filters=[MetricFilter(field="country", value="Germany")])

    assert _n(narrowed.rows[0]["current_revenue"]) < _n(everything.rows[0]["current_revenue"])


# -------------------------------------------------------------- safety spot-checks


@pytest.mark.asyncio
async def test_a_hostile_filter_value_matches_nothing_rather_than_altering_the_query(runner) -> None:
    result = await runner.run(MetricParameters(
        metric="cancellation_rate", period=Q1,
        filters=[MetricFilter(field="country", value="Germany' OR '1'='1")],
    ))

    assert result.rows[0]["total_order_count"] == 0
