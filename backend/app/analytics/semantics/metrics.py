"""Runtime-owned, versioned business metric definitions (not database content).

A definition is the only place a metric's SQL, its groupable dimensions and its
filterable fields are written down. The compiler emits nothing that is not
declared here, which is what makes a reader-supplied rerun safe: the request
chooses among these, it never contributes to them.

Metrics without a ``sql_template`` are documentation for the agent, which writes
its own SQL and has it validated at execution. Those cannot be rerun without an
agent turn, and ``is_rerunnable`` says so.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.analytics.semantics.parameters import FilterOperator

#: Every operator, for fields where all comparisons make sense.
ALL_OPERATORS: tuple[FilterOperator, ...] = ("eq", "ne", "in", "not_in", "gt", "gte", "lt", "lte")
#: Comparisons that make sense for a label rather than a quantity.
LABEL_OPERATORS: tuple[FilterOperator, ...] = ("eq", "ne", "in", "not_in")

#: Where a definition stands, from guidance-only through to production use.
#:
#:   documented       - no compiled SQL. The agent reads this as guidance and
#:                      writes its own statement, validated at execution the
#:                      same way as any other agent-written query.
#:   executable       - compiles to a statement the AST validator accepts and
#:                      runs against the schema, but has not yet been proven
#:                      against this file's written business definition by a
#:                      dedicated correctness test suite.
#:   validated        - executable, and a fixture-based test suite proves it
#:                      matches its written definition: the normal case, an
#:                      empty period, nulls, a zero denominator, boundary
#:                      timestamps, and its declared dimensions and filters.
#:   production_ready - validated, and already relied on elsewhere in the
#:                      system (a report template, the acceptance-test
#:                      pipeline) rather than only by its own tests.
#:
#: The UI and API expose only "executable" and above as something a reader
#: may rerun; "documented" never appears as if it were executable.
MetricLifecycleStatus = Literal["documented", "executable", "validated", "production_ready"]


class DimensionSpec(BaseModel):
    """One grouping a metric supports, and the SQL that expresses it.

    ``expression`` is emitted into the statement verbatim, so it is written here
    by a developer and never assembled from a request.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str = Field(min_length=1, max_length=64)
    expression: str = Field(min_length=1, max_length=200)
    #: The output column name. Also the key a report reads the value under.
    alias: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")


class FilterSpec(BaseModel):
    """One field a metric may be narrowed by, and how it may be compared."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str = Field(min_length=1, max_length=64)
    #: The qualified column. Emitted verbatim; never taken from a request.
    column: str = Field(min_length=1, max_length=200)
    operators: tuple[FilterOperator, ...] = LABEL_OPERATORS
    value_type: Literal["string", "number", "boolean"] = "string"


class MetricDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    version: str = "v1"
    display_name: str
    description: str
    formula: str
    grain: str
    required_tables: list[str]
    dimensions: list[str]
    time_column: str | None = None
    unit: str
    format: Literal["currency", "percent", "number", "duration", "rating"]
    business_caveats: list[str] = Field(default_factory=list)
    #: The statement this metric compiles to, with ``{dimensions}``,
    #: ``{filters}`` and ``{group_by}`` slots the compiler fills from the
    #: declarations below. Absent for metrics the agent still writes by hand.
    sql_template: str | None = None
    #: The result columns that carry values, in reported order.
    value_columns: tuple[str, ...] = ()
    #: Groupings a rerun may request, by name.
    dimension_specs: dict[str, DimensionSpec] = Field(default_factory=dict)
    #: Fields a rerun may filter on, by name.
    filter_specs: dict[str, FilterSpec] = Field(default_factory=dict)
    #: Time buckets a ``period`` dimension may use.
    supported_grains: tuple[str, ...] = ("day", "week", "month", "quarter", "year")
    #: See ``MetricLifecycleStatus``. Defaults to the state a definition with
    #: no compiled SQL is actually in, so a new documentation-only entry
    #: never has to remember to set this.
    status: MetricLifecycleStatus = "documented"

    @model_validator(mode="after")
    def _status_matches_what_is_actually_compiled(self) -> "MetricDefinition":
        has_sql = bool(self.sql_template and self.value_columns)
        if self.status == "documented" and has_sql:
            raise ValueError(
                f"{self.name}: a compiled metric (sql_template and value_columns set) "
                "cannot be status 'documented'."
            )
        if self.status != "documented" and not has_sql:
            raise ValueError(
                f"{self.name}: status {self.status!r} requires both sql_template and "
                "value_columns to be set."
            )
        return self

    @property
    def identifier(self) -> str: return f"{self.name}:{self.version}"

    @property
    def is_rerunnable(self) -> bool:
        """Whether this metric can be recomputed without an agent turn."""

        return self.status != "documented" and bool(self.sql_template and self.value_columns)


class MetricRegistry:
    def __init__(self, definitions: list[MetricDefinition] | None = None) -> None:
        self._definitions = {item.name: item for item in (definitions or DEFAULT_METRICS)}
    def list_metrics(self) -> list[MetricDefinition]: return sorted(self._definitions.values(), key=lambda item: item.name)
    def list_rerunnable(self) -> list[MetricDefinition]:
        """The metrics a reader may recompute by changing report parameters."""
        return [item for item in self.list_metrics() if item.is_rerunnable]
    def get_metric_definition(self, name: str) -> MetricDefinition | None: return self._definitions.get(name.lower())
    def find_metrics(self, query: str) -> list[MetricDefinition]:
        q=query.lower().strip(); return [item for item in self.list_metrics() if q in item.name or q in item.display_name.lower() or q in item.description.lower()]


def _m(name, display, formula, tables, dims, time, unit, fmt, caveats=(), **compiled):
    return MetricDefinition(name=name, display_name=display, description=display, formula=formula, grain="aggregate over selected period and dimensions", required_tables=tables, dimensions=dims, time_column=time, unit=unit, format=fmt, business_caveats=list(caveats), **compiled)


# --------------------------------------------------------------- shared pieces

#: Order-side groupings. Written once because four metrics share them.
#:
#: ``order_date`` is a timestamptz, so every bucket and every bound is taken in
#: UTC explicitly. Without that, ``date_trunc`` follows the session timezone and
#: a January order lands in December on a server set to anything east of UTC —
#: a silent off-by-one-month in a published total.
_ORDER_DIMENSIONS = {
    "period": DimensionSpec(label="Period", expression="date_trunc('{grain}', o.order_date AT TIME ZONE 'UTC')", alias="period"),
    "country": DimensionSpec(label="Billing country", expression="o.billing_country", alias="country"),
    "status": DimensionSpec(label="Order status", expression="o.status", alias="status"),
}
_ORDER_FILTERS = {
    "country": FilterSpec(label="Billing country", column="o.billing_country"),
    "shipping_country": FilterSpec(label="Shipping country", column="o.shipping_country"),
    "campaign_id": FilterSpec(label="Campaign", column="o.campaign_id", operators=ALL_OPERATORS, value_type="number"),
}

_REVENUE_SQL = """
SELECT {dimensions}
       SUM(o.total_amount) AS revenue,
       COUNT(DISTINCT o.id) AS order_count
FROM orders AS o
WHERE o.status = 'delivered'
  AND (o.order_date AT TIME ZONE 'UTC') >= :period_start
  AND (o.order_date AT TIME ZONE 'UTC') < :period_end
  {filters}
{group_by}
""".strip()

_ORDER_COUNT_SQL = """
SELECT {dimensions}
       COUNT(DISTINCT o.id) AS order_count
FROM orders AS o
WHERE o.status = 'delivered'
  AND (o.order_date AT TIME ZONE 'UTC') >= :period_start
  AND (o.order_date AT TIME ZONE 'UTC') < :period_end
  {filters}
{group_by}
""".strip()

_GROSS_PROFIT_SQL = """
SELECT {dimensions}
       SUM(i.line_total - i.unit_cost * i.quantity) AS gross_profit,
       SUM(i.line_total) AS line_revenue
FROM orders AS o
JOIN order_items AS i ON i.order_id = o.id
WHERE o.status = 'delivered'
  AND (o.order_date AT TIME ZONE 'UTC') >= :period_start
  AND (o.order_date AT TIME ZONE 'UTC') < :period_end
  {filters}
{group_by}
""".strip()

_PAYMENT_FAILURE_SQL = """
SELECT {dimensions}
       COUNT(*) AS failure_count,
       SUM(p.amount) AS failed_amount
FROM payments AS p
JOIN payment_methods AS m ON m.id = p.payment_method_id
WHERE p.status = 'failed'
  AND (p.attempted_at AT TIME ZONE 'UTC') >= :period_start
  AND (p.attempted_at AT TIME ZONE 'UTC') < :period_end
  {filters}
{group_by}
""".strip()

#: Attainment is divided inside the statement, never in Python: a ratio the
#: renderer computed would be a number no query produced. A zero target yields
#: NULL rather than an error, and a FULL OUTER JOIN keeps a month that has a
#: target but no orders as well as one with orders but no target.
_TARGET_ATTAINMENT_SQL = """
WITH actuals AS (
    SELECT date_part('year', o.order_date AT TIME ZONE 'UTC') AS year,
           date_part('month', o.order_date AT TIME ZONE 'UTC') AS month,
           SUM(o.total_amount) AS revenue_actual,
           COUNT(DISTINCT o.id) AS order_actual
    FROM orders AS o
    WHERE o.status = 'delivered'
      AND (o.order_date AT TIME ZONE 'UTC') >= :period_start
      AND (o.order_date AT TIME ZONE 'UTC') < :period_end
      {filters}
    GROUP BY 1, 2
), profit AS (
    SELECT date_part('year', o.order_date AT TIME ZONE 'UTC') AS year,
           date_part('month', o.order_date AT TIME ZONE 'UTC') AS month,
           SUM(i.line_total - i.unit_cost * i.quantity) AS gross_profit_actual
    FROM orders AS o
    JOIN order_items AS i ON i.order_id = o.id
    WHERE o.status = 'delivered'
      AND (o.order_date AT TIME ZONE 'UTC') >= :period_start
      AND (o.order_date AT TIME ZONE 'UTC') < :period_end
    GROUP BY 1, 2
), targets AS (
    SELECT t.year, t.month, t.revenue_target, t.gross_profit_target, t.order_target
    FROM monthly_targets AS t
    WHERE make_date(t.year, t.month, 1) >= :period_start
      AND make_date(t.year, t.month, 1) < :period_end
)
SELECT to_char(make_date(COALESCE(t.year, a.year)::int, COALESCE(t.month, a.month)::int, 1),
               'YYYY-MM') AS period,
       a.revenue_actual,
       t.revenue_target,
       CASE WHEN t.revenue_target IS NULL OR t.revenue_target = 0 THEN NULL
            ELSE ROUND(100.0 * a.revenue_actual / t.revenue_target, 2) END AS revenue_attainment_pct,
       a.order_actual,
       t.order_target,
       CASE WHEN t.order_target IS NULL OR t.order_target = 0 THEN NULL
            ELSE ROUND(100.0 * a.order_actual / t.order_target, 2) END AS order_attainment_pct,
       p.gross_profit_actual,
       t.gross_profit_target,
       CASE WHEN t.gross_profit_target IS NULL OR t.gross_profit_target = 0 THEN NULL
            ELSE ROUND(100.0 * p.gross_profit_actual / t.gross_profit_target, 2) END AS gross_profit_attainment_pct
FROM targets AS t
FULL OUTER JOIN actuals AS a ON a.year = t.year AND a.month = t.month
LEFT JOIN profit AS p ON p.year = COALESCE(t.year, a.year) AND p.month = COALESCE(t.month, a.month)
ORDER BY 1, 2
""".strip()


# ----------------------------------------------------------------- group 1

_GROSS_MARGIN_SQL = """
SELECT {dimensions}
       SUM(i.line_total - i.unit_cost * i.quantity) AS gross_profit,
       SUM(i.line_total) AS line_revenue,
       CASE WHEN SUM(i.line_total) IS NULL OR SUM(i.line_total) = 0 THEN NULL
            ELSE ROUND(100.0 * SUM(i.line_total - i.unit_cost * i.quantity) / SUM(i.line_total), 2) END AS gross_margin_pct
FROM orders AS o
JOIN order_items AS i ON i.order_id = o.id
WHERE o.status = 'delivered'
  AND (o.order_date AT TIME ZONE 'UTC') >= :period_start
  AND (o.order_date AT TIME ZONE 'UTC') < :period_end
  {filters}
{group_by}
""".strip()

_AVERAGE_ORDER_VALUE_SQL = """
SELECT {dimensions}
       SUM(o.total_amount) AS total_revenue,
       COUNT(DISTINCT o.id) AS order_count,
       CASE WHEN COUNT(DISTINCT o.id) = 0 THEN NULL
            ELSE ROUND(SUM(o.total_amount) / COUNT(DISTINCT o.id), 2) END AS average_order_value
FROM orders AS o
WHERE o.status = 'delivered'
  AND (o.order_date AT TIME ZONE 'UTC') >= :period_start
  AND (o.order_date AT TIME ZONE 'UTC') < :period_end
  {filters}
{group_by}
""".strip()

_CUSTOMER_COUNT_SQL = """
SELECT {dimensions}
       COUNT(DISTINCT o.customer_id) AS customer_count
FROM orders AS o
WHERE o.status = 'delivered'
  AND (o.order_date AT TIME ZONE 'UTC') >= :period_start
  AND (o.order_date AT TIME ZONE 'UTC') < :period_end
  {filters}
{group_by}
""".strip()

#: New customers are counted by signup, not by first order: ``customers`` is
#: the acquisition record and pairs with ``monthly_targets.new_customer_target``,
#: while "first delivered order in period" would be a different, behavioural
#: definition this metric does not claim to answer.
_NEW_CUSTOMERS_SQL = """
SELECT {dimensions}
       COUNT(*) AS new_customer_count
FROM customers AS c
WHERE c.signup_date >= :period_start
  AND c.signup_date < :period_end
  {filters}
{group_by}
""".strip()

#: A customer counts as repeat when they placed two or more delivered orders
#: within the requested period itself -- not over their lifetime. Grouping by
#: a dimension is not offered: a customer's orders can span countries or
#: channels, so there is no single dimension value to attribute a repeat
#: customer's row to.
_REPEAT_CUSTOMER_RATE_SQL = """
WITH customer_orders AS (
    SELECT o.customer_id, COUNT(DISTINCT o.id) AS delivered_order_count
    FROM orders AS o
    WHERE o.status = 'delivered'
      AND (o.order_date AT TIME ZONE 'UTC') >= :period_start
      AND (o.order_date AT TIME ZONE 'UTC') < :period_end
      {filters}
    GROUP BY o.customer_id
)
SELECT COUNT(*) FILTER (WHERE delivered_order_count >= 2) AS repeat_customer_count,
       COUNT(*) AS customer_count,
       CASE WHEN COUNT(*) = 0 THEN NULL
            ELSE ROUND(100.0 * COUNT(*) FILTER (WHERE delivered_order_count >= 2) / COUNT(*), 2) END AS repeat_customer_rate_pct
FROM customer_orders
""".strip()

#: Scoped to delivered orders in the period, matching the written formula's
#: denominator; only a refund whose own status is 'processed' counts, and a
#: refund is attributed to the order's placement date, not the refund's own
#: request or processed date.
_REFUND_RATE_SQL = """
SELECT {dimensions}
       COUNT(DISTINCT r.order_id) AS refunded_order_count,
       COUNT(DISTINCT o.id) AS delivered_order_count,
       CASE WHEN COUNT(DISTINCT o.id) = 0 THEN NULL
            ELSE ROUND(100.0 * COUNT(DISTINCT r.order_id) / COUNT(DISTINCT o.id), 2) END AS refund_rate_pct
FROM orders AS o
LEFT JOIN refunds AS r ON r.order_id = o.id AND r.status = 'processed'
WHERE o.status = 'delivered'
  AND (o.order_date AT TIME ZONE 'UTC') >= :period_start
  AND (o.order_date AT TIME ZONE 'UTC') < :period_end
  {filters}
{group_by}
""".strip()

#: Every order placed in the period is the denominator here, not only
#: delivered ones -- cancellation is a fate an order meets instead of
#: delivery, so restricting to delivered orders first would make the rate
#: zero by construction.
_CANCELLATION_RATE_SQL = """
SELECT {dimensions}
       COUNT(*) FILTER (WHERE o.status = 'cancelled') AS cancelled_order_count,
       COUNT(*) AS total_order_count,
       CASE WHEN COUNT(*) = 0 THEN NULL
            ELSE ROUND(100.0 * COUNT(*) FILTER (WHERE o.status = 'cancelled') / COUNT(*), 2) END AS cancellation_rate_pct
FROM orders AS o
WHERE (o.order_date AT TIME ZONE 'UTC') >= :period_start
  AND (o.order_date AT TIME ZONE 'UTC') < :period_end
  {filters}
{group_by}
""".strip()

#: ``converted`` is the session's own recorded outcome, not inferred from the
#: presence of ``order_id``: a session can carry an order id without being
#: marked converted, so the boolean is the authoritative signal.
_CONVERSION_RATE_SQL = """
SELECT {dimensions}
       COUNT(*) FILTER (WHERE ws.converted) AS converted_session_count,
       COUNT(*) AS session_count,
       CASE WHEN COUNT(*) = 0 THEN NULL
            ELSE ROUND(100.0 * COUNT(*) FILTER (WHERE ws.converted) / COUNT(*), 2) END AS conversion_rate_pct
FROM web_sessions AS ws
WHERE (ws.started_at AT TIME ZONE 'UTC') >= :period_start
  AND (ws.started_at AT TIME ZONE 'UTC') < :period_end
  {filters}
{group_by}
""".strip()

_UNITS_SOLD_SQL = """
SELECT {dimensions}
       SUM(i.quantity) AS units_sold
FROM orders AS o
JOIN order_items AS i ON i.order_id = o.id
JOIN products AS pr ON pr.id = i.product_id
JOIN product_categories AS pc ON pc.id = pr.category_id
WHERE o.status = 'delivered'
  AND (o.order_date AT TIME ZONE 'UTC') >= :period_start
  AND (o.order_date AT TIME ZONE 'UTC') < :period_end
  {filters}
{group_by}
""".strip()

#: Growth against the immediately preceding period of equal length, derived
#: entirely from the requested period's own bounds -- no second period is
#: accepted from a caller. A calendar month-over-month or year-over-year
#: comparison is a different, equally defensible definition; this is the one
#: general enough to answer for any period shape a reader asks for.
_REVENUE_GROWTH_SQL = """
WITH bounds AS (
    SELECT CAST(:period_start AS date) AS period_start,
           CAST(:period_end AS date) AS period_end,
           (CAST(:period_start AS date) - (CAST(:period_end AS date) - CAST(:period_start AS date))) AS prior_start
),
current_period AS (
    SELECT SUM(o.total_amount) AS revenue, COUNT(DISTINCT o.id) AS order_count
    FROM orders AS o, bounds AS b
    WHERE o.status = 'delivered'
      AND (o.order_date AT TIME ZONE 'UTC') >= b.period_start
      AND (o.order_date AT TIME ZONE 'UTC') < b.period_end
      {filters}
),
prior_period AS (
    SELECT SUM(o.total_amount) AS revenue, COUNT(DISTINCT o.id) AS order_count
    FROM orders AS o, bounds AS b
    WHERE o.status = 'delivered'
      AND (o.order_date AT TIME ZONE 'UTC') >= b.prior_start
      AND (o.order_date AT TIME ZONE 'UTC') < b.period_start
      {filters}
)
SELECT c.revenue AS current_revenue,
       p.revenue AS prior_revenue,
       CASE WHEN p.revenue IS NULL OR p.revenue = 0 THEN NULL
            ELSE ROUND(100.0 * (c.revenue - p.revenue) / p.revenue, 2) END AS revenue_growth_pct,
       c.order_count AS current_order_count,
       p.order_count AS prior_order_count
FROM current_period AS c, prior_period AS p
""".strip()


# ----------------------------------------------------------------- group 2

_PAYMENT_SUCCESS_SQL = """
SELECT {dimensions}
       COUNT(*) FILTER (WHERE p.status = 'completed') AS success_count,
       COUNT(*) AS attempt_count,
       CASE WHEN COUNT(*) = 0 THEN NULL
            ELSE ROUND(100.0 * COUNT(*) FILTER (WHERE p.status = 'completed') / COUNT(*), 2) END AS payment_success_rate_pct
FROM payments AS p
JOIN payment_methods AS m ON m.id = p.payment_method_id
WHERE (p.attempted_at AT TIME ZONE 'UTC') >= :period_start
  AND (p.attempted_at AT TIME ZONE 'UTC') < :period_end
  {filters}
{group_by}
""".strip()

_LATE_DELIVERY_RATE_SQL = """
SELECT {dimensions}
       COUNT(*) FILTER (WHERE s.delivered_at > s.expected_delivery_at) AS late_count,
       COUNT(*) AS delivered_count,
       CASE WHEN COUNT(*) = 0 THEN NULL
            ELSE ROUND(100.0 * COUNT(*) FILTER (WHERE s.delivered_at > s.expected_delivery_at) / COUNT(*), 2) END AS late_delivery_rate_pct
FROM shipments AS s
JOIN warehouses AS w ON w.id = s.warehouse_id
WHERE s.delivered_at IS NOT NULL
  AND (s.delivered_at AT TIME ZONE 'UTC') >= :period_start
  AND (s.delivered_at AT TIME ZONE 'UTC') < :period_end
  {filters}
{group_by}
""".strip()

_AVERAGE_DELIVERY_TIME_SQL = """
SELECT {dimensions}
       ROUND(AVG(EXTRACT(EPOCH FROM (s.delivered_at - s.shipped_at)) / 86400.0)::numeric, 2) AS average_delivery_days,
       COUNT(*) AS shipment_count
FROM shipments AS s
JOIN warehouses AS w ON w.id = s.warehouse_id
WHERE s.delivered_at IS NOT NULL
  AND (s.delivered_at AT TIME ZONE 'UTC') >= :period_start
  AND (s.delivered_at AT TIME ZONE 'UTC') < :period_end
  {filters}
{group_by}
""".strip()

_AVERAGE_REVIEW_RATING_SQL = """
SELECT {dimensions}
       ROUND(AVG(r.rating)::numeric, 2) AS average_rating,
       COUNT(*) AS review_count
FROM reviews AS r
JOIN products AS pr ON pr.id = r.product_id
JOIN product_categories AS pc ON pc.id = pr.category_id
WHERE (r.created_at AT TIME ZONE 'UTC') >= :period_start
  AND (r.created_at AT TIME ZONE 'UTC') < :period_end
  {filters}
{group_by}
""".strip()


# ------------------------------------------------------- group 1/2 dimensions

#: Customer-table groupings, keyed off signup rather than order activity.
_CUSTOMER_DIMENSIONS = {
    "period": DimensionSpec(label="Period", expression="date_trunc('{grain}', c.signup_date)", alias="period"),
    "country": DimensionSpec(label="Country", expression="c.country", alias="country"),
    "acquisition_channel": DimensionSpec(label="Acquisition channel", expression="c.acquisition_channel", alias="acquisition_channel"),
}
_CUSTOMER_FILTERS = {
    "country": FilterSpec(label="Country", column="c.country"),
    "acquisition_channel": FilterSpec(label="Acquisition channel", column="c.acquisition_channel"),
}

_SESSION_DIMENSIONS = {
    "period": DimensionSpec(label="Period", expression="date_trunc('{grain}', ws.started_at AT TIME ZONE 'UTC')", alias="period"),
    "country": DimensionSpec(label="Country", expression="ws.country", alias="country"),
    "device": DimensionSpec(label="Device type", expression="ws.device_type", alias="device"),
    "channel": DimensionSpec(label="Acquisition channel", expression="ws.acquisition_channel", alias="channel"),
}
_SESSION_FILTERS = {
    "country": FilterSpec(label="Country", column="ws.country"),
    "device": FilterSpec(label="Device type", column="ws.device_type"),
    "channel": FilterSpec(label="Acquisition channel", column="ws.acquisition_channel"),
    "campaign_id": FilterSpec(label="Campaign", column="ws.campaign_id", operators=ALL_OPERATORS, value_type="number"),
}

_UNITS_SOLD_DIMENSIONS = {
    "period": DimensionSpec(label="Period", expression="date_trunc('{grain}', o.order_date AT TIME ZONE 'UTC')", alias="period"),
    "category": DimensionSpec(label="Category", expression="pc.name", alias="category"),
    "product": DimensionSpec(label="Product", expression="pr.name", alias="product"),
}
_UNITS_SOLD_FILTERS = {
    "category": FilterSpec(label="Category", column="pc.name"),
    "product": FilterSpec(label="Product", column="pr.name"),
    "country": FilterSpec(label="Billing country", column="o.billing_country"),
}

_PAYMENT_SUCCESS_DIMENSIONS = {
    "period": DimensionSpec(label="Period", expression="date_trunc('{grain}', p.attempted_at AT TIME ZONE 'UTC')", alias="period"),
    "payment_method": DimensionSpec(label="Payment method", expression="m.name", alias="payment_method"),
    "provider": DimensionSpec(label="Provider", expression="m.provider", alias="provider"),
}
_PAYMENT_SUCCESS_FILTERS = {
    "payment_method": FilterSpec(label="Payment method", column="m.name"),
    "provider": FilterSpec(label="Provider", column="m.provider"),
}

_SHIPMENT_DIMENSIONS = {
    "period": DimensionSpec(label="Period", expression="date_trunc('{grain}', s.delivered_at AT TIME ZONE 'UTC')", alias="period"),
    "warehouse": DimensionSpec(label="Warehouse", expression="w.name", alias="warehouse"),
    "carrier": DimensionSpec(label="Carrier", expression="s.carrier", alias="carrier"),
}
_SHIPMENT_FILTERS = {
    "warehouse": FilterSpec(label="Warehouse", column="w.name"),
    "carrier": FilterSpec(label="Carrier", column="s.carrier"),
}

_REVIEW_DIMENSIONS = {
    "period": DimensionSpec(label="Period", expression="date_trunc('{grain}', r.created_at AT TIME ZONE 'UTC')", alias="period"),
    "product": DimensionSpec(label="Product", expression="pr.name", alias="product"),
    "category": DimensionSpec(label="Category", expression="pc.name", alias="category"),
}
#: No boolean-valued filter is declared here. `MetricFilter.value`'s
#: `str | int | float | bool` union under `union_mode="left_to_right"`
#: matches a real `True`/`False` against `int` first (`bool` is an `int`
#: subclass in Python), so it never reaches `_check_value_type`'s boolean
#: branch as an actual bool -- a pre-existing gap in the shared filter
#: contract, out of this change's scope to fix. A `verified_purchase` filter
#: is a natural addition once that is corrected separately.
_REVIEW_FILTERS = {
    "product": FilterSpec(label="Product", column="pr.name"),
    "category": FilterSpec(label="Category", column="pc.name"),
}


DEFAULT_METRICS = [
 _m("revenue","Revenue","SUM(orders.total_amount) for delivered orders",["orders"],["time","country","campaign"],"orders.order_date","USD","currency",["Excludes cancelled and refunded orders."],
    sql_template=_REVENUE_SQL, value_columns=("revenue", "order_count"),
    dimension_specs=_ORDER_DIMENSIONS, filter_specs=_ORDER_FILTERS, status="production_ready"),
 _m("net_revenue","Net Revenue","SUM(delivered orders.total_amount) - SUM(processed refunds.amount)",["orders","refunds"],["time","country","campaign"],"orders.order_date","USD","currency",["Refund timing may differ from order timing."]),
 _m("gross_profit","Gross Profit","SUM(order_items.line_total - order_items.unit_cost * order_items.quantity) for delivered orders",["orders","order_items"],["time","country","category","product","campaign"],"orders.order_date","USD","currency",(),
    sql_template=_GROSS_PROFIT_SQL, value_columns=("gross_profit", "line_revenue"),
    dimension_specs=_ORDER_DIMENSIONS, filter_specs=_ORDER_FILTERS, status="production_ready"),
 _m("gross_margin_pct","Gross Margin %","100 * gross_profit / SUM(order_items.line_total) for delivered orders",["orders","order_items"],["time","category","product"],"orders.order_date","percent","percent",["Returns NULL when revenue denominator is zero."],
    sql_template=_GROSS_MARGIN_SQL, value_columns=("gross_profit", "line_revenue", "gross_margin_pct"),
    dimension_specs=_ORDER_DIMENSIONS, filter_specs=_ORDER_FILTERS, status="validated"),
 _m("orders","Orders","COUNT(DISTINCT delivered orders.id)",["orders"],["time","country","campaign"],"orders.order_date","orders","number",(),
    sql_template=_ORDER_COUNT_SQL, value_columns=("order_count",),
    dimension_specs=_ORDER_DIMENSIONS, filter_specs=_ORDER_FILTERS, status="production_ready"),
 _m("units_sold","Units Sold","SUM(order_items.quantity) for delivered orders",["orders","order_items","products","product_categories"],["time","category","product"],"orders.order_date","units","number",(),
    sql_template=_UNITS_SOLD_SQL, value_columns=("units_sold",),
    dimension_specs=_UNITS_SOLD_DIMENSIONS, filter_specs=_UNITS_SOLD_FILTERS, status="validated"),
 _m("average_order_value","Average Order Value","SUM(delivered orders.total_amount) / COUNT(DISTINCT delivered orders.id)",["orders"],["time","country","campaign"],"orders.order_date","USD","currency",["Returns NULL when no delivered orders exist."],
    sql_template=_AVERAGE_ORDER_VALUE_SQL, value_columns=("total_revenue", "order_count", "average_order_value"),
    dimension_specs=_ORDER_DIMENSIONS, filter_specs=_ORDER_FILTERS, status="validated"),
 _m("refund_rate","Refund Rate","100 * COUNT(DISTINCT processed refunds.order_id) / COUNT(DISTINCT delivered orders.id)",["orders","refunds"],["time","country","category"],"orders.order_date","percent","percent",["Order-based rate; partial refunds count once per order.","Scoped to the order's placement date, not the refund's request date."],
    sql_template=_REFUND_RATE_SQL, value_columns=("refunded_order_count", "delivered_order_count", "refund_rate_pct"),
    dimension_specs=_ORDER_DIMENSIONS, filter_specs=_ORDER_FILTERS, status="validated"),
 _m("payment_failure_count","Payment Failures","COUNT(failed payments), optionally by method and failure reason",["payments","payment_methods"],["time","payment_method","failure_reason"],"payments.attempted_at","payments","number",["Counts attempts, not distinct orders."],
    sql_template=_PAYMENT_FAILURE_SQL, value_columns=("failure_count", "failed_amount"), status="production_ready",
    dimension_specs={
        "period": DimensionSpec(label="Period", expression="date_trunc('{grain}', p.attempted_at AT TIME ZONE 'UTC')", alias="period"),
        "payment_method": DimensionSpec(label="Payment method", expression="m.name", alias="payment_method"),
        "failure_reason": DimensionSpec(label="Failure reason", expression="p.failure_reason", alias="failure_reason"),
        "provider": DimensionSpec(label="Provider", expression="m.provider", alias="provider"),
    },
    filter_specs={
        "payment_method": FilterSpec(label="Payment method", column="m.name"),
        "failure_reason": FilterSpec(label="Failure reason", column="p.failure_reason"),
        "provider": FilterSpec(label="Provider", column="m.provider"),
    }),
 _m("payment_failure_rate","Payment Failure Rate","100 * COUNT(failed payments) / COUNT(all payment attempts)",["payments"],["time","payment_method"],"payments.attempted_at","percent","percent",["Returns NULL with no attempts."]),
 _m("target_attainment","Target Attainment","Delivered revenue, orders and gross profit against monthly_targets, with attainment computed in SQL",["orders","order_items","monthly_targets"],["month"],"orders.order_date","percent","percent",
    ["A month with a target but no delivered orders reports a null actual.",
     "A month with orders but no target reports a null target and no attainment.",
     "A zero target yields no attainment rather than an error.",
     "Gross profit is joined per month and is null where no items were delivered."],
    sql_template=_TARGET_ATTAINMENT_SQL,
    value_columns=("period",
                   "revenue_actual", "revenue_target", "revenue_attainment_pct",
                   "order_actual", "order_target", "order_attainment_pct",
                   "gross_profit_actual", "gross_profit_target", "gross_profit_attainment_pct"),
    # Always reported per month: the join is on the target calendar.
    dimension_specs={}, filter_specs={"country": FilterSpec(label="Billing country", column="o.billing_country")},
    supported_grains=("month",), status="production_ready"),
 _m("conversion_rate","Conversion Rate","100 * COUNT(web_sessions.converted) / COUNT(web_sessions)",["web_sessions"],["time","country","channel","device"],"web_sessions.started_at","percent","percent",
    ["converted is the session's own recorded outcome; a session may carry an order_id without being marked converted."],
    sql_template=_CONVERSION_RATE_SQL, value_columns=("converted_session_count", "session_count", "conversion_rate_pct"),
    dimension_specs=_SESSION_DIMENSIONS, filter_specs=_SESSION_FILTERS, status="validated"),
 _m("cart_to_checkout_rate","Cart to Checkout Rate","100 * sessions with checkout event / sessions with cart event",["web_events"],["time","device","channel"],"web_events.event_time","percent","percent",["Event types must be verified in the dataset."]),
 _m("checkout_to_purchase_rate","Checkout to Purchase Rate","100 * sessions with purchase event / sessions with checkout event",["web_events"],["time","device","channel"],"web_events.event_time","percent","percent",["Event types must be verified in the dataset."]),
 _m("repeat_purchase_rate","Repeat Customer Rate","100 * customers with 2+ delivered orders in the period / customers with a delivered order in the period",["orders"],["country"],"orders.order_date","percent","percent",
    ["Repeat status is evaluated within the requested period, not over a customer's full history.",
     "No dimension breakdown: a repeat customer's orders can span more than one country or channel."],
    sql_template=_REPEAT_CUSTOMER_RATE_SQL, value_columns=("repeat_customer_count", "customer_count", "repeat_customer_rate_pct"),
    dimension_specs={}, filter_specs=_ORDER_FILTERS, supported_grains=(), status="validated"),
 _m("average_delivery_time","Average Delivery Time","AVG(delivered_at - shipped_at) in days, for delivered shipments",["shipments","warehouses"],["time","warehouse","carrier"],"shipments.delivered_at","days","duration",
    ["Excludes shipments with no delivered_at recorded yet."],
    sql_template=_AVERAGE_DELIVERY_TIME_SQL, value_columns=("average_delivery_days", "shipment_count"),
    dimension_specs=_SHIPMENT_DIMENSIONS, filter_specs=_SHIPMENT_FILTERS, status="validated"),
 _m("late_delivery_rate","Delayed Order Rate","100 * delivered shipments after expected_delivery_at / delivered shipments",["shipments","warehouses"],["time","warehouse","carrier"],"shipments.delivered_at","percent","percent",
    ["Excludes shipments with no delivered_at recorded yet, so an order still in transit is not counted either way."],
    sql_template=_LATE_DELIVERY_RATE_SQL, value_columns=("late_count", "delivered_count", "late_delivery_rate_pct"),
    dimension_specs=_SHIPMENT_DIMENSIONS, filter_specs=_SHIPMENT_FILTERS, status="validated"),
 _m("customer_lifetime_revenue","Customer Lifetime Revenue","SUM(delivered orders.total_amount) per customer",["orders"],["customer","country","customer segment"],"orders.order_date","USD","currency"),
 _m("campaign_attributed_revenue","Campaign Attributed Revenue","SUM(campaign_attribution.attributed_revenue)",["campaign_attribution","campaigns"],["time","campaign","channel"],"campaign_attribution.created_at","USD","currency",["Uses the stored attribution model."]),
 _m("campaign_roas","Campaign ROAS","SUM(attributed_revenue) / campaigns.budget",["campaign_attribution","campaigns"],["time","campaign","channel"],"campaign_attribution.created_at","ratio","number",["Budget and attribution period alignment must be checked."]),
 _m("inventory_stockout_rate","Inventory Stockout Rate","100 * COUNT(inventory rows with quantity_available <= 0) / COUNT(inventory rows)",["inventory"],["time","warehouse","product","category"],"inventory.updated_at","percent","percent",
    ["Left documentation-only: `inventory` is a single current-state snapshot, not a period history. "
     "Every row in the seeded data shares one updated_at timestamp, so a period predicate over it would "
     "return all rows or none rather than a genuine 'stockout rate during this period'. A true period-based "
     "answer needs a dated inventory-snapshot or ledger table, which the schema does not have.",
     "quantity_available <= 0 never occurs in the seeded data; reorder_level-based low-stock would be the "
     "more useful current-state signal, but still cannot honestly be scoped to a reader-chosen period."]),
 _m("return_rate","Return Rate","100 * physically returned units / units sold",["inventory_movements","order_items"],["time","category","product"],"inventory_movements.created_at","percent","percent",
    ["Left documentation-only: inventory_movements has no rows of movement_type='return' in the seeded data, "
     "and its only populated rows (movement_type='sale') all share one created_at timestamp, so it is a bulk "
     "snapshot rather than a genuine movement ledger. There is no schema-backed way to distinguish a physical "
     "product return from a refund. refund_rate is the closest honestly-supported proxy."]),
 _m("payment_success_rate","Payment Success Rate","100 * COUNT(completed payments) / COUNT(all payment attempts)",["payments","payment_methods"],["time","payment_method","provider"],"payments.attempted_at","percent","percent",
    ["Counts attempts, not distinct orders; complements payment_failure_count."],
    sql_template=_PAYMENT_SUCCESS_SQL, value_columns=("success_count", "attempt_count", "payment_success_rate_pct"),
    dimension_specs=_PAYMENT_SUCCESS_DIMENSIONS, filter_specs=_PAYMENT_SUCCESS_FILTERS, status="validated"),
 _m("average_review_rating","Average Review Score","AVG(reviews.rating)",["reviews","products","product_categories"],["time","product","category"],"reviews.created_at","stars","rating",["Reviewers are a self-selected population."],
    sql_template=_AVERAGE_REVIEW_RATING_SQL, value_columns=("average_rating", "review_count"),
    dimension_specs=_REVIEW_DIMENSIONS, filter_specs=_REVIEW_FILTERS, status="validated"),
 _m("customer_count","Customer Count","COUNT(DISTINCT customer_id) with a delivered order in the period",["orders"],["time","country","campaign"],"orders.order_date","customers","number",
    ["Counts customers active (had a delivered order) in the period, not the full customer base to date."],
    sql_template=_CUSTOMER_COUNT_SQL, value_columns=("customer_count",),
    dimension_specs=_ORDER_DIMENSIONS, filter_specs=_ORDER_FILTERS, status="validated"),
 _m("new_customers","New Customers","COUNT(customers) whose signup_date falls in the period",["customers"],["time","country","acquisition_channel"],"customers.signup_date","customers","number",
    ["Counts by signup date (acquisition), not by a customer's first delivered order."],
    sql_template=_NEW_CUSTOMERS_SQL, value_columns=("new_customer_count",),
    dimension_specs=_CUSTOMER_DIMENSIONS, filter_specs=_CUSTOMER_FILTERS, status="validated"),
 _m("cancellation_rate","Cancellation Rate","100 * COUNT(cancelled orders) / COUNT(all orders placed in the period)",["orders"],["time","country","campaign"],"orders.order_date","percent","percent",
    ["Denominator is every order placed in the period regardless of outcome, not only delivered orders."],
    sql_template=_CANCELLATION_RATE_SQL, value_columns=("cancelled_order_count", "total_order_count", "cancellation_rate_pct"),
    dimension_specs=_ORDER_DIMENSIONS, filter_specs=_ORDER_FILTERS, status="validated"),
 _m("revenue_growth","Revenue Growth","100 * (current period revenue - prior period revenue) / prior period revenue",["orders"],["country","campaign"],"orders.order_date","percent","percent",
    ["Compares the requested period to the immediately preceding period of equal length, derived from the "
     "request's own bounds; not a calendar month-over-month or year-over-year comparison.",
     "No period/dimension regrouping: the metric already consumes the period as a single before/after comparison."],
    sql_template=_REVENUE_GROWTH_SQL,
    value_columns=("current_revenue", "prior_revenue", "revenue_growth_pct", "current_order_count", "prior_order_count"),
    dimension_specs={}, filter_specs=_ORDER_FILTERS, supported_grains=(), status="validated"),
]
