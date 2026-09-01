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

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.semantics.parameters import FilterOperator

#: Every operator, for fields where all comparisons make sense.
ALL_OPERATORS: tuple[FilterOperator, ...] = ("eq", "ne", "in", "not_in", "gt", "gte", "lt", "lte")
#: Comparisons that make sense for a label rather than a quantity.
LABEL_OPERATORS: tuple[FilterOperator, ...] = ("eq", "ne", "in", "not_in")


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

    @property
    def identifier(self) -> str: return f"{self.name}:{self.version}"

    @property
    def is_rerunnable(self) -> bool:
        """Whether this metric can be recomputed without an agent turn."""

        return bool(self.sql_template and self.value_columns)


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


DEFAULT_METRICS = [
 _m("revenue","Revenue","SUM(orders.total_amount) for delivered orders",["orders"],["time","country","campaign"],"orders.order_date","USD","currency",["Excludes cancelled and refunded orders."],
    sql_template=_REVENUE_SQL, value_columns=("revenue", "order_count"),
    dimension_specs=_ORDER_DIMENSIONS, filter_specs=_ORDER_FILTERS),
 _m("net_revenue","Net Revenue","SUM(delivered orders.total_amount) - SUM(processed refunds.amount)",["orders","refunds"],["time","country","campaign"],"orders.order_date","USD","currency",["Refund timing may differ from order timing."]),
 _m("gross_profit","Gross Profit","SUM(order_items.line_total - order_items.unit_cost * order_items.quantity) for delivered orders",["orders","order_items"],["time","country","category","product","campaign"],"orders.order_date","USD","currency",(),
    sql_template=_GROSS_PROFIT_SQL, value_columns=("gross_profit", "line_revenue"),
    dimension_specs=_ORDER_DIMENSIONS, filter_specs=_ORDER_FILTERS),
 _m("gross_margin_pct","Gross Margin %","100 * gross_profit / SUM(order_items.line_total) for delivered orders",["orders","order_items"],["time","category","product"],"orders.order_date","percent","percent",["Returns NULL when revenue denominator is zero."]),
 _m("orders","Orders","COUNT(DISTINCT delivered orders.id)",["orders"],["time","country","campaign"],"orders.order_date","orders","number",(),
    sql_template=_ORDER_COUNT_SQL, value_columns=("order_count",),
    dimension_specs=_ORDER_DIMENSIONS, filter_specs=_ORDER_FILTERS),
 _m("units_sold","Units Sold","SUM(order_items.quantity) for delivered orders",["orders","order_items"],["time","category","product"],"orders.order_date","units","number"),
 _m("average_order_value","Average Order Value","SUM(delivered orders.total_amount) / COUNT(DISTINCT delivered orders.id)",["orders"],["time","country","campaign"],"orders.order_date","USD","currency",["Returns NULL when no delivered orders exist."]),
 _m("refund_rate","Refund Rate","100 * COUNT(DISTINCT processed refunds.order_id) / COUNT(DISTINCT delivered orders.id)",["orders","refunds"],["time","country","category"],"orders.order_date","percent","percent",["Order-based rate; partial refunds count once per order."]),
 _m("payment_failure_count","Payment Failures","COUNT(failed payments), optionally by method and failure reason",["payments","payment_methods"],["time","payment_method","failure_reason"],"payments.attempted_at","payments","number",["Counts attempts, not distinct orders."],
    sql_template=_PAYMENT_FAILURE_SQL, value_columns=("failure_count", "failed_amount"),
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
    supported_grains=("month",)),
 _m("conversion_rate","Conversion Rate","100 * COUNT(converted web_sessions) / COUNT(web_sessions)",["web_sessions"],["time","country","channel","device","campaign"],"web_sessions.started_at","percent","percent"),
 _m("cart_to_checkout_rate","Cart to Checkout Rate","100 * sessions with checkout event / sessions with cart event",["web_events"],["time","device","channel"],"web_events.event_time","percent","percent",["Event types must be verified in the dataset."]),
 _m("checkout_to_purchase_rate","Checkout to Purchase Rate","100 * sessions with purchase event / sessions with checkout event",["web_events"],["time","device","channel"],"web_events.event_time","percent","percent",["Event types must be verified in the dataset."]),
 _m("repeat_purchase_rate","Repeat Purchase Rate","100 * customers with at least two delivered orders / customers with delivered orders",["orders"],["time","country","customer segment"],"orders.order_date","percent","percent"),
 _m("average_delivery_time","Average Delivery Time","AVG(delivered_at - shipped_at) for delivered shipments",["shipments"],["time","warehouse","carrier"],"shipments.delivered_at","days","duration",["Excludes unfinished shipments."]),
 _m("late_delivery_rate","Late Delivery Rate","100 * delivered shipments after expected_delivery_at / delivered shipments with expected date",["shipments"],["time","warehouse","carrier"],"shipments.delivered_at","percent","percent"),
 _m("customer_lifetime_revenue","Customer Lifetime Revenue","SUM(delivered orders.total_amount) per customer",["orders"],["customer","country","customer segment"],"orders.order_date","USD","currency"),
 _m("campaign_attributed_revenue","Campaign Attributed Revenue","SUM(campaign_attribution.attributed_revenue)",["campaign_attribution","campaigns"],["time","campaign","channel"],"campaign_attribution.created_at","USD","currency",["Uses the stored attribution model."]),
 _m("campaign_roas","Campaign ROAS","SUM(attributed_revenue) / campaigns.budget",["campaign_attribution","campaigns"],["time","campaign","channel"],"campaign_attribution.created_at","ratio","number",["Budget and attribution period alignment must be checked."]),
 _m("inventory_stockout_rate","Inventory Stockout Rate","100 * COUNT(inventory rows with quantity_available <= 0) / COUNT(inventory rows)",["inventory"],["time","warehouse","product","category"],"inventory.updated_at","percent","percent"),
 _m("average_review_rating","Average Review Rating","AVG(reviews.rating)",["reviews"],["time","product","category"],"reviews.created_at","stars","rating",["Reviewers are a self-selected population."]),
]
