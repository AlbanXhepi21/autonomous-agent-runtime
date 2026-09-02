"""Compiling a reader's parameters into a statement they could not have written.

The security story is that a request never contributes SQL text: it chooses
among declarations, and its values are bound. These tests attack that from the
request side — hostile fields, unknown dimensions, wrong operators, wrong types
— and check the compiled output from the other side, against the same AST
validator that guards the agent's own SQL.
"""

from datetime import date

import pytest

from app.analytics.schema.allowlist import AnalyticsSchemaPolicy
from app.analytics.semantics.compiler import (
    MetricCompilationError,
    compile_metric,
)
from app.analytics.semantics.metrics import MetricRegistry
from app.analytics.semantics.parameters import (
    MAX_PERIOD_DAYS,
    MetricFilter,
    MetricParameters,
    ReportPeriod,
)
from app.analytics.sql.validator import PostgreSQLQueryValidator

REGISTRY = MetricRegistry()
VALIDATOR = PostgreSQLQueryValidator(AnalyticsSchemaPolicy.configured("public"))
ALLOWED_TABLES = [
    "orders", "order_items", "payments", "payment_methods", "monthly_targets",
    "refunds", "customers", "products", "product_categories", "web_sessions",
    "shipments", "warehouses", "reviews",
]
#: The metrics this phase compiles. Anything else still needs an agent turn.
ENABLED = [
    "revenue", "orders", "gross_profit", "payment_failure_count", "target_attainment",
    # Group 1
    "average_order_value", "gross_margin_pct", "customer_count", "new_customers",
    "repeat_purchase_rate", "refund_rate", "cancellation_rate", "conversion_rate",
    "units_sold", "revenue_growth",
    # Group 2
    "payment_success_rate", "late_delivery_rate", "average_delivery_time", "average_review_rating",
]
#: Group 1 and Group 2 metrics added in this phase, without the five already
#: compiled beforehand. Used to scope the new per-metric parametrized tests
#: below without repeating assertions already made for the original five.
NEW_METRICS = [name for name in ENABLED if name not in {
    "revenue", "orders", "gross_profit", "payment_failure_count", "target_attainment",
}]
#: Metrics that intentionally decline dimension regrouping, because their
#: computation already consumes the period as a single derived aggregate.
NO_DIMENSION_METRICS = {"repeat_purchase_rate", "revenue_growth"}

Q1 = ReportPeriod(start=date(2026, 1, 1), end=date(2026, 4, 1))


def _compile(metric: str, **overrides):
    parameters = MetricParameters(metric=metric, period=overrides.pop("period", Q1), **overrides)
    return compile_metric(REGISTRY.get_metric_definition(metric), parameters)


def _validate(compiled):
    return VALIDATOR.validate(compiled.sql, allowed_tables=ALLOWED_TABLES)


# ------------------------------------------------------------------- periods


def test_a_period_is_half_open() -> None:
    """The last day is excluded, so a month boundary is neither lost nor doubled."""

    period = ReportPeriod(start=date(2026, 1, 1), end=date(2026, 2, 1))

    assert period.describe() == "2026-01-01 to 2026-01-31"


def test_a_single_day_period_reads_as_one_date() -> None:
    assert ReportPeriod(start=date(2026, 1, 1), end=date(2026, 1, 2)).describe() == "2026-01-01"


@pytest.mark.parametrize("start,end", [
    (date(2026, 4, 1), date(2026, 1, 1)),   # backwards
    (date(2026, 1, 1), date(2026, 1, 1)),   # empty
])
def test_an_impossible_period_is_refused(start: date, end: date) -> None:
    with pytest.raises(ValueError):
        ReportPeriod(start=start, end=end)


def test_an_unbounded_period_is_refused() -> None:
    """One request may not ask for a scan of the whole table."""

    from datetime import timedelta

    start = date(2000, 1, 1)
    with pytest.raises(ValueError, match="five years"):
        ReportPeriod(start=start, end=start + timedelta(days=MAX_PERIOD_DAYS + 1))


@pytest.mark.parametrize("value", ["not-a-date", "2026-13-01", "", None, 20260101])
def test_an_invalid_date_never_becomes_a_period(value: object) -> None:
    with pytest.raises(ValueError):
        ReportPeriod(start=value, end=date(2026, 2, 1))  # type: ignore[arg-type]


def test_a_period_binds_rather_than_inlining_its_dates() -> None:
    compiled = _compile("revenue")

    assert ":period_start" in compiled.sql and ":period_end" in compiled.sql
    assert "2026-01-01" not in compiled.sql
    assert compiled.parameters["period_start"] == date(2026, 1, 1)
    assert compiled.parameters["period_end"] == date(2026, 4, 1)


# ---------------------------------------------------------------- dimensions


@pytest.mark.parametrize("metric,dimension", [
    ("revenue", "period"), ("revenue", "country"), ("orders", "country"),
    ("payment_failure_count", "payment_method"), ("payment_failure_count", "failure_reason"),
])
def test_a_declared_dimension_compiles_and_validates(metric: str, dimension: str) -> None:
    compiled = _compile(metric, dimensions=[dimension])

    assert dimension in compiled.dimension_columns
    assert "GROUP BY 1" in compiled.sql
    assert _validate(compiled).valid


@pytest.mark.parametrize("dimension", [
    "product", "customer_email", "o.billing_country", "1; DROP TABLE orders",
    "revenue) AS x, (SELECT 1", "",
])
def test_an_undeclared_dimension_is_refused(dimension: str) -> None:
    """Including anything shaped like SQL: it is looked up, never interpreted."""

    with pytest.raises((MetricCompilationError, ValueError)):
        _compile("revenue", dimensions=[dimension])


def test_a_dimension_the_metric_does_not_have_names_what_it_does() -> None:
    with pytest.raises(MetricCompilationError, match="payment_method"):
        _compile("revenue", dimensions=["payment_method"])


def test_two_dimensions_group_and_order_by_both() -> None:
    compiled = _compile("payment_failure_count", dimensions=["payment_method", "failure_reason"])

    assert compiled.dimension_columns == ("payment_method", "failure_reason")
    assert "GROUP BY 1, 2" in compiled.sql and "ORDER BY 1, 2" in compiled.sql
    assert _validate(compiled).valid


def test_a_dimension_cannot_be_requested_twice() -> None:
    with pytest.raises(ValueError, match="only once"):
        MetricParameters(metric="revenue", period=Q1, dimensions=["country", "country"])


@pytest.mark.parametrize("grain", ["month", "quarter", "year", "day", "week"])
def test_every_supported_grain_compiles(grain: str) -> None:
    compiled = _compile("revenue", dimensions=["period"], grain=grain)

    assert f"date_trunc('{grain}'" in compiled.sql
    assert _validate(compiled).valid


def test_target_attainment_is_always_reported_per_month() -> None:
    """It is joined onto the target calendar, so it declares no regrouping."""

    with pytest.raises(MetricCompilationError, match="cannot be grouped by 'period'"):
        _compile("target_attainment", dimensions=["period"])


def test_a_grain_the_metric_does_not_support_is_refused() -> None:
    """A metric may restrict which buckets its period dimension allows."""

    from app.analytics.semantics.metrics import DimensionSpec

    monthly_only = REGISTRY.get_metric_definition("revenue").model_copy(
        update={"supported_grains": ("month",),
                "dimension_specs": {"period": DimensionSpec(
                    label="Period",
                    expression="date_trunc('{grain}', o.order_date AT TIME ZONE 'UTC')",
                    alias="period")}},
    )

    with pytest.raises(MetricCompilationError, match="cannot be grouped by day"):
        compile_metric(monthly_only, MetricParameters(
            metric="revenue", period=Q1, dimensions=["period"], grain="day"))


def test_a_grain_outside_the_closed_set_never_reaches_compilation() -> None:
    with pytest.raises(ValueError):
        MetricParameters(metric="revenue", period=Q1, grain="century'); DROP TABLE orders--")  # type: ignore[arg-type]


def test_timestamps_are_bucketed_in_utc() -> None:
    """Session timezone must not decide which month an order belongs to."""

    compiled = _compile("revenue", dimensions=["period"])

    assert "AT TIME ZONE 'UTC'" in compiled.sql
    # Both the bucket and the period bounds, or the two disagree at a boundary.
    assert compiled.sql.count("AT TIME ZONE 'UTC'") >= 3


# ------------------------------------------------------------------- filters


def test_a_declared_filter_binds_its_value() -> None:
    compiled = _compile("revenue", filters=[MetricFilter(field="country", value="Germany")])

    assert "o.billing_country = :filter_0" in compiled.sql
    assert compiled.parameters["filter_0"] == "Germany"
    assert "Germany" not in compiled.sql
    assert _validate(compiled).valid


def test_a_membership_filter_binds_every_member() -> None:
    compiled = _compile("revenue", filters=[
        MetricFilter(field="country", operator="in", value=["Germany", "France", "Italy"]),
    ])

    assert "IN (:filter_0_0, :filter_0_1, :filter_0_2)" in compiled.sql
    assert [compiled.parameters[f"filter_0_{index}"] for index in range(3)] == [
        "Germany", "France", "Italy",
    ]
    assert _validate(compiled).valid


def test_several_filters_each_bind_separately() -> None:
    compiled = _compile("revenue", filters=[
        MetricFilter(field="country", value="Germany"),
        MetricFilter(field="shipping_country", operator="ne", value="France"),
    ])

    assert compiled.parameters["filter_0"] == "Germany"
    assert compiled.parameters["filter_1"] == "France"
    assert _validate(compiled).valid


@pytest.mark.parametrize("field", [
    "total_amount", "o.billing_country", "unknown", "1=1", "country; DROP TABLE orders",
])
def test_an_undeclared_filter_field_is_refused(field: str) -> None:
    with pytest.raises(MetricCompilationError, match="cannot be filtered"):
        _compile("revenue", filters=[MetricFilter(field=field, value="x")])


def test_an_operator_the_field_does_not_allow_is_refused() -> None:
    """A country is a label; asking whether it is greater than one is not a question."""

    with pytest.raises(MetricCompilationError, match="does not support"):
        _compile("revenue", filters=[MetricFilter(field="country", operator="gt", value="Germany")])


def test_an_operator_outside_the_closed_set_never_reaches_compilation() -> None:
    with pytest.raises(ValueError):
        MetricFilter(field="country", operator="LIKE '%' OR 1=1--", value="x")  # type: ignore[arg-type]


def test_a_value_of_the_wrong_type_is_refused() -> None:
    with pytest.raises(MetricCompilationError, match="expects a number"):
        _compile("revenue", filters=[MetricFilter(field="campaign_id", value="not-a-number")])


def test_a_numeric_field_accepts_a_number_and_binds_it() -> None:
    compiled = _compile("revenue", filters=[
        MetricFilter(field="campaign_id", operator="gte", value=12),
    ])

    assert "o.campaign_id >= :filter_0" in compiled.sql
    assert compiled.parameters["filter_0"] == 12


def test_a_structure_is_never_accepted_as_a_filter_value() -> None:
    with pytest.raises(ValueError):
        MetricFilter(field="country", value={"$ne": None})  # type: ignore[arg-type]


def test_a_membership_filter_is_bounded() -> None:
    with pytest.raises(ValueError, match="at most 50"):
        MetricFilter(field="country", operator="in", value=[str(n) for n in range(51)])


@pytest.mark.parametrize("operator", ["in", "not_in"])
def test_a_membership_operator_needs_a_list(operator: str) -> None:
    with pytest.raises(ValueError, match="needs a list"):
        MetricFilter(field="country", operator=operator, value="Germany")  # type: ignore[arg-type]


def test_a_comparison_operator_refuses_a_list() -> None:
    with pytest.raises(ValueError, match="needs a single value"):
        MetricFilter(field="country", operator="eq", value=["Germany"])


# ---------------------------------------------------------- compiled output


@pytest.mark.parametrize("metric", ENABLED)
def test_every_enabled_metric_compiles_to_a_statement_the_validator_accepts(metric: str) -> None:
    """The compiler is not trusted on its own; the AST validator is the gate."""

    compiled = _compile(metric)
    result = _validate(compiled)

    assert result.valid, f"{metric}: {result.reason}"
    assert result.statement_type == "SELECT"
    assert set(result.referenced_tables) <= set(ALLOWED_TABLES)


@pytest.mark.parametrize("metric", ENABLED)
def test_a_compiled_statement_is_a_single_read_only_select(metric: str) -> None:
    compiled = _compile(metric)

    assert compiled.sql.lstrip().upper().startswith(("SELECT", "WITH"))
    assert ";" not in compiled.sql, "a compiled statement must not be separable"
    for forbidden in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "GRANT", "COPY"):
        assert forbidden not in compiled.sql.upper()


@pytest.mark.parametrize("metric", ENABLED)
def test_a_compiled_statement_reports_the_columns_it_declares(metric: str) -> None:
    definition = REGISTRY.get_metric_definition(metric)
    compiled = _compile(metric)

    assert compiled.value_columns == definition.value_columns
    for column in definition.value_columns:
        assert column in compiled.sql


def test_a_fingerprint_identifies_the_shape_not_the_values() -> None:
    """The same question over two periods is recognisably the same question."""

    first = _compile("revenue")
    second = _compile("revenue", period=ReportPeriod(start=date(2025, 1, 1), end=date(2025, 4, 1)))
    grouped = _compile("revenue", dimensions=["country"])

    assert first.fingerprint == second.fingerprint
    assert first.fingerprint != grouped.fingerprint


def test_a_metric_without_a_template_cannot_be_recomputed() -> None:
    """It is documentation for the agent, not something a reader may rerun."""

    definition = REGISTRY.get_metric_definition("cart_to_checkout_rate")

    assert not definition.is_rerunnable
    assert definition.status == "documented"
    with pytest.raises(MetricCompilationError, match="agent turn"):
        _compile("cart_to_checkout_rate")


@pytest.mark.parametrize("metric", [
    "net_revenue", "payment_failure_rate", "cart_to_checkout_rate", "checkout_to_purchase_rate",
    "customer_lifetime_revenue", "campaign_attributed_revenue", "campaign_roas",
    "inventory_stockout_rate", "return_rate",
])
def test_every_remaining_documentation_only_metric_declines_execution(metric: str) -> None:
    """The UI and API must not be able to represent these as executable."""

    definition = REGISTRY.get_metric_definition(metric)

    assert definition.status == "documented"
    assert not definition.is_rerunnable
    assert definition.sql_template is None
    with pytest.raises(MetricCompilationError, match="agent turn"):
        _compile(metric)


def test_inventory_stockout_rate_and_return_rate_explain_their_missing_data() -> None:
    """Left documentation-only on purpose; the reason must be readable, not silent."""

    stockout = REGISTRY.get_metric_definition("inventory_stockout_rate")
    returns = REGISTRY.get_metric_definition("return_rate")

    assert any("snapshot" in caveat for caveat in stockout.business_caveats)
    assert any("ledger" in caveat or "movement" in caveat for caveat in returns.business_caveats)


def test_the_registry_lists_exactly_the_metrics_this_phase_enabled() -> None:
    assert sorted(item.name for item in REGISTRY.list_rerunnable()) == sorted(ENABLED)


def test_a_request_naming_a_different_metric_than_its_definition_is_refused() -> None:
    with pytest.raises(MetricCompilationError, match="different metrics"):
        compile_metric(
            REGISTRY.get_metric_definition("revenue"),
            MetricParameters(metric="orders", period=Q1),
        )


def test_target_attainment_divides_inside_the_statement() -> None:
    """A ratio computed in Python would be a figure no query produced."""

    compiled = _compile("target_attainment")

    assert "revenue_attainment_pct" in compiled.sql
    assert "/ t.revenue_target" in compiled.sql
    # Zero and missing targets are handled in SQL, not by a later guard.
    assert "IS NULL OR t.revenue_target = 0" in compiled.sql
    assert "FULL OUTER JOIN" in compiled.sql
    assert _validate(compiled).valid


# --------------------------------------------------------- group 1 / group 2


def test_every_newly_enabled_metric_has_a_lifecycle_status_beyond_documented() -> None:
    for name in NEW_METRICS:
        definition = REGISTRY.get_metric_definition(name)
        assert definition.status != "documented", name
        assert definition.is_rerunnable, name


@pytest.mark.parametrize("metric", NEW_METRICS)
def test_every_new_metric_compiles_to_a_statement_the_validator_accepts(metric: str) -> None:
    compiled = _compile(metric)
    result = _validate(compiled)

    assert result.valid, f"{metric}: {result.reason}"
    assert result.statement_type == "SELECT"
    assert set(result.referenced_tables) <= set(ALLOWED_TABLES), f"{metric}: {result.referenced_tables}"


@pytest.mark.parametrize("metric", NEW_METRICS)
def test_every_new_metric_reports_the_columns_it_declares(metric: str) -> None:
    definition = REGISTRY.get_metric_definition(metric)
    compiled = _compile(metric)

    assert compiled.value_columns == definition.value_columns
    for column in definition.value_columns:
        assert column in compiled.sql


@pytest.mark.parametrize("metric", NEW_METRICS)
def test_every_new_metric_computes_its_ratio_or_average_inside_sql(metric: str) -> None:
    """A percentage, an average or a growth figure must come out of the statement."""

    definition = REGISTRY.get_metric_definition(metric)
    compiled = _compile(metric)

    if definition.format in {"percent", "duration"} or metric in {"average_review_rating", "revenue_growth"}:
        assert any(
            keyword in compiled.sql for keyword in ("CASE WHEN", "ROUND(", "AVG(")
        ), f"{metric}: expected a SQL-computed ratio or average"


@pytest.mark.parametrize("metric,dimension", [
    ("average_order_value", "period"), ("average_order_value", "country"),
    ("gross_margin_pct", "period"), ("gross_margin_pct", "country"),
    ("customer_count", "period"), ("customer_count", "country"),
    ("new_customers", "period"), ("new_customers", "acquisition_channel"),
    ("refund_rate", "period"), ("refund_rate", "country"),
    ("cancellation_rate", "period"), ("cancellation_rate", "country"),
    ("conversion_rate", "period"), ("conversion_rate", "device"), ("conversion_rate", "channel"),
    ("units_sold", "period"), ("units_sold", "category"), ("units_sold", "product"),
    ("payment_success_rate", "payment_method"), ("payment_success_rate", "provider"),
    ("late_delivery_rate", "warehouse"), ("late_delivery_rate", "carrier"),
    ("average_delivery_time", "warehouse"), ("average_delivery_time", "carrier"),
    ("average_review_rating", "product"), ("average_review_rating", "category"),
])
def test_a_new_metrics_declared_dimension_compiles_and_validates(metric: str, dimension: str) -> None:
    compiled = _compile(metric, dimensions=[dimension])

    assert dimension in compiled.dimension_columns
    assert "GROUP BY 1" in compiled.sql
    assert _validate(compiled).valid


@pytest.mark.parametrize("metric", NEW_METRICS)
def test_a_new_metric_rejects_an_undeclared_dimension(metric: str) -> None:
    with pytest.raises(MetricCompilationError):
        _compile(metric, dimensions=["not_a_real_dimension"])


@pytest.mark.parametrize("metric", NO_DIMENSION_METRICS)
def test_a_dimensionless_metric_rejects_even_its_own_period(metric: str) -> None:
    """Some metrics already consume the period as a single before/after or
    population comparison, so regrouping by period is not offered either."""

    with pytest.raises(MetricCompilationError, match="cannot be grouped by 'period'"):
        _compile(metric, dimensions=["period"])


@pytest.mark.parametrize("metric,field,value", [
    ("average_order_value", "country", "Germany"),
    ("gross_margin_pct", "campaign_id", 3),
    ("customer_count", "shipping_country", "France"),
    ("new_customers", "country", "Germany"),
    ("new_customers", "acquisition_channel", "email"),
    ("refund_rate", "country", "Germany"),
    ("cancellation_rate", "country", "Germany"),
    ("conversion_rate", "country", "Germany"),
    ("conversion_rate", "device", "mobile"),
    ("units_sold", "category", "Electronics"),
    ("payment_success_rate", "payment_method", "Visa"),
    ("late_delivery_rate", "carrier", "DHL"),
    ("average_delivery_time", "warehouse", "Berlin"),
    ("average_review_rating", "product", "Widget"),
    ("revenue_growth", "country", "Germany"),
    ("repeat_purchase_rate", "country", "Germany"),
])
def test_a_new_metrics_declared_filter_binds_its_value(metric: str, field: str, value: object) -> None:
    compiled = _compile(metric, filters=[MetricFilter(field=field, value=value)])

    assert ":filter_0" in compiled.sql
    assert compiled.parameters["filter_0"] == value
    assert str(value) not in compiled.sql
    assert _validate(compiled).valid


@pytest.mark.parametrize("metric", NEW_METRICS)
def test_a_new_metric_rejects_an_undeclared_filter(metric: str) -> None:
    with pytest.raises(MetricCompilationError, match="cannot be filtered"):
        _compile(metric, filters=[MetricFilter(field="not_a_real_filter", value="x")])


@pytest.mark.parametrize("metric,field", [
    ("average_order_value", "country"),
    ("new_customers", "country"),
    ("units_sold", "category"),
    ("average_review_rating", "product"),
])
def test_a_new_metrics_label_filter_rejects_a_numeric_comparison(metric: str, field: str) -> None:
    """A country or a product name is a label; 'greater than' is not a question it answers."""

    with pytest.raises(MetricCompilationError, match="does not support"):
        _compile(metric, filters=[MetricFilter(field=field, operator="gt", value="Germany")])


def test_revenue_growth_compares_the_period_to_its_own_immediate_predecessor() -> None:
    """The prior window is derived from the request's own bounds, never a second period."""

    compiled = _compile("revenue_growth")

    assert "prior_start" in compiled.sql
    assert "CAST(:period_start AS date)" in compiled.sql
    assert set(compiled.parameters) == {"period_start", "period_end"}
    assert _validate(compiled).valid


def test_cancellation_rate_does_not_restrict_to_delivered_orders() -> None:
    """The denominator must be every order placed, or cancellations could never appear in it."""

    compiled = _compile("cancellation_rate")

    assert "o.status = 'delivered'" not in compiled.sql
    assert "o.status = 'cancelled'" in compiled.sql
    assert _validate(compiled).valid


def test_refund_rate_only_counts_processed_refunds_on_delivered_orders() -> None:
    compiled = _compile("refund_rate")

    assert "r.status = 'processed'" in compiled.sql
    assert "o.status = 'delivered'" in compiled.sql
    assert _validate(compiled).valid


def test_new_customers_is_scoped_by_signup_date_not_first_order() -> None:
    compiled = _compile("new_customers")

    assert "FROM customers AS c" in compiled.sql
    assert "orders" not in compiled.sql
    assert _validate(compiled).valid


def test_late_delivery_and_average_delivery_time_exclude_undelivered_shipments() -> None:
    for metric in ("late_delivery_rate", "average_delivery_time"):
        compiled = _compile(metric)
        assert "s.delivered_at IS NOT NULL" in compiled.sql, metric
        assert _validate(compiled).valid
