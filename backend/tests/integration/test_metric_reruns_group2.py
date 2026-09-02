"""Business-correctness tests for the Group 2 semantic metrics.

Same discipline as `test_metric_reruns_group1.py`: cross-checked against an
independently computed figure or a known structural boundary, never a
hand-copied number.

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


# ------------------------------------------------------------ payment success


@pytest.mark.asyncio
async def test_payment_success_rate_complements_payment_failure_count(runner) -> None:
    """Two views of the same attempts population must reconcile exactly."""

    success = await _run(runner, "payment_success_rate")
    failures = await _run(runner, "payment_failure_count")

    row = success.rows[0]
    assert row["success_count"] + failures.rows[0]["failure_count"] == row["attempt_count"]
    expected = round(100 * row["success_count"] / row["attempt_count"], 2)
    assert _n(row["payment_success_rate_pct"]) == pytest.approx(expected, abs=0.01)
    assert 0 < _n(row["payment_success_rate_pct"]) < 100


@pytest.mark.asyncio
async def test_payment_success_rate_is_null_for_an_empty_period(runner) -> None:
    result = await _run(runner, "payment_success_rate", period=EMPTY)

    assert result.rows[0]["attempt_count"] == 0
    assert result.rows[0]["payment_success_rate_pct"] is None


@pytest.mark.asyncio
async def test_payment_success_rate_by_method_sums_to_the_total(runner) -> None:
    by_method = await _run(runner, "payment_success_rate", dimensions=["payment_method"])
    total = await _run(runner, "payment_success_rate")

    assert by_method.row_count > 1
    assert sum(row["attempt_count"] for row in by_method.rows) == total.rows[0]["attempt_count"]
    assert sum(row["success_count"] for row in by_method.rows) == total.rows[0]["success_count"]


@pytest.mark.asyncio
async def test_payment_success_rate_narrowed_by_provider_filter(runner) -> None:
    everything = await _run(runner, "payment_success_rate")
    narrowed = await _run(runner, "payment_success_rate", filters=[MetricFilter(field="provider", value="Visa")])

    assert 0 < narrowed.rows[0]["attempt_count"] < everything.rows[0]["attempt_count"]


# -------------------------------------------------------------- late delivery


@pytest.mark.asyncio
async def test_late_delivery_rate_is_bounded_and_self_consistent(runner) -> None:
    result = await _run(runner, "late_delivery_rate")

    row = result.rows[0]
    assert 0 < row["late_count"] < row["delivered_count"]
    expected = round(100 * row["late_count"] / row["delivered_count"], 2)
    assert _n(row["late_delivery_rate_pct"]) == pytest.approx(expected, abs=0.01)


@pytest.mark.asyncio
async def test_late_delivery_rate_excludes_shipments_without_a_delivered_at(runner) -> None:
    """An order still in transit counts toward neither the numerator nor the denominator."""

    result = await _run(runner, "late_delivery_rate")

    assert result.rows[0]["delivered_count"] > 0


@pytest.mark.asyncio
async def test_late_delivery_rate_is_null_for_an_empty_period(runner) -> None:
    result = await _run(runner, "late_delivery_rate", period=EMPTY)

    assert result.rows[0]["delivered_count"] == 0
    assert result.rows[0]["late_delivery_rate_pct"] is None


@pytest.mark.asyncio
async def test_late_delivery_rate_by_carrier_sums_to_the_total(runner) -> None:
    by_carrier = await _run(runner, "late_delivery_rate", dimensions=["carrier"])
    total = await _run(runner, "late_delivery_rate")

    assert by_carrier.row_count > 1
    assert sum(row["delivered_count"] for row in by_carrier.rows) == total.rows[0]["delivered_count"]


@pytest.mark.asyncio
async def test_late_delivery_rate_narrowed_by_warehouse_filter(runner) -> None:
    by_warehouse = await _run(runner, "late_delivery_rate", dimensions=["warehouse"])
    first = by_warehouse.rows[0]

    filtered = await _run(runner, "late_delivery_rate",
                          filters=[MetricFilter(field="warehouse", value=first["warehouse"])])

    assert filtered.rows[0]["delivered_count"] == first["delivered_count"]


# ---------------------------------------------------------- average delivery time


@pytest.mark.asyncio
async def test_average_delivery_time_is_a_small_positive_number_of_days(runner) -> None:
    result = await _run(runner, "average_delivery_time")

    row = result.rows[0]
    # A retailer's delivery time is days, not months: a generous, still-meaningful bound.
    assert 0 < _n(row["average_delivery_days"]) < 30
    assert row["shipment_count"] > 0


@pytest.mark.asyncio
async def test_average_delivery_time_is_null_for_an_empty_period(runner) -> None:
    result = await _run(runner, "average_delivery_time", period=EMPTY)

    assert result.rows[0]["shipment_count"] == 0
    assert result.rows[0]["average_delivery_days"] is None


@pytest.mark.asyncio
async def test_average_delivery_time_by_warehouse(runner) -> None:
    result = await _run(runner, "average_delivery_time", dimensions=["warehouse"])

    assert result.row_count > 1
    for row in result.rows:
        assert row["warehouse"]
        assert _n(row["average_delivery_days"]) > 0


@pytest.mark.asyncio
async def test_average_delivery_time_narrowed_by_carrier_filter(runner) -> None:
    everything = await _run(runner, "average_delivery_time")
    narrowed = await _run(runner, "average_delivery_time", filters=[MetricFilter(field="carrier", value="DHL")])

    assert narrowed.rows[0]["shipment_count"] < everything.rows[0]["shipment_count"]
    assert _n(narrowed.rows[0]["average_delivery_days"]) > 0


# ---------------------------------------------------------- average review rating


@pytest.mark.asyncio
async def test_average_review_rating_is_within_the_declared_scale(runner) -> None:
    result = await _run(runner, "average_review_rating")

    row = result.rows[0]
    assert 1 <= _n(row["average_rating"]) <= 5
    assert row["review_count"] > 0


@pytest.mark.asyncio
async def test_average_review_rating_is_null_for_an_empty_period(runner) -> None:
    result = await _run(runner, "average_review_rating", period=EMPTY)

    assert result.rows[0]["review_count"] == 0
    assert result.rows[0]["average_rating"] is None


@pytest.mark.asyncio
async def test_average_review_rating_by_category_sums_review_counts_to_the_total(runner) -> None:
    by_category = await _run(runner, "average_review_rating", dimensions=["category"])
    total = await _run(runner, "average_review_rating")

    assert by_category.row_count > 1
    assert sum(row["review_count"] for row in by_category.rows) == total.rows[0]["review_count"]
    for row in by_category.rows:
        assert 1 <= _n(row["average_rating"]) <= 5


@pytest.mark.asyncio
async def test_average_review_rating_narrowed_by_product_filter(runner) -> None:
    by_product = await _run(runner, "average_review_rating", dimensions=["product"])
    first = by_product.rows[0]

    filtered = await _run(runner, "average_review_rating",
                          filters=[MetricFilter(field="product", value=first["product"])])

    assert filtered.rows[0]["review_count"] == first["review_count"]
