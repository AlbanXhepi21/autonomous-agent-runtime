"""Runtime-owned, versioned business metric definitions (not database content)."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


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
    sql_template: str | None = None

    @property
    def identifier(self) -> str: return f"{self.name}:{self.version}"


class MetricRegistry:
    def __init__(self, definitions: list[MetricDefinition] | None = None) -> None:
        self._definitions = {item.name: item for item in (definitions or DEFAULT_METRICS)}
    def list_metrics(self) -> list[MetricDefinition]: return sorted(self._definitions.values(), key=lambda item: item.name)
    def get_metric_definition(self, name: str) -> MetricDefinition | None: return self._definitions.get(name.lower())
    def find_metrics(self, query: str) -> list[MetricDefinition]:
        q=query.lower().strip(); return [item for item in self.list_metrics() if q in item.name or q in item.display_name.lower() or q in item.description.lower()]


def _m(name, display, formula, tables, dims, time, unit, fmt, caveats=()):
    return MetricDefinition(name=name, display_name=display, description=display, formula=formula, grain="aggregate over selected period and dimensions", required_tables=tables, dimensions=dims, time_column=time, unit=unit, format=fmt, business_caveats=list(caveats))


DEFAULT_METRICS = [
 _m("revenue","Revenue","SUM(orders.total_amount) for delivered orders",["orders"],["time","country","campaign"],"orders.order_date","USD","currency",["Excludes cancelled and refunded orders."]),
 _m("net_revenue","Net Revenue","SUM(delivered orders.total_amount) - SUM(processed refunds.amount)",["orders","refunds"],["time","country","campaign"],"orders.order_date","USD","currency",["Refund timing may differ from order timing."]),
 _m("gross_profit","Gross Profit","SUM(order_items.line_total - order_items.unit_cost * order_items.quantity) for delivered orders",["orders","order_items"],["time","country","category","product","campaign"],"orders.order_date","USD","currency"),
 _m("gross_margin_pct","Gross Margin %","100 * gross_profit / SUM(order_items.line_total) for delivered orders",["orders","order_items"],["time","category","product"],"orders.order_date","percent","percent",["Returns NULL when revenue denominator is zero."]),
 _m("orders","Orders","COUNT(DISTINCT delivered orders.id)",["orders"],["time","country","campaign"],"orders.order_date","orders","number"),
 _m("units_sold","Units Sold","SUM(order_items.quantity) for delivered orders",["orders","order_items"],["time","category","product"],"orders.order_date","units","number"),
 _m("average_order_value","Average Order Value","SUM(delivered orders.total_amount) / COUNT(DISTINCT delivered orders.id)",["orders"],["time","country","campaign"],"orders.order_date","USD","currency",["Returns NULL when no delivered orders exist."]),
 _m("refund_rate","Refund Rate","100 * COUNT(DISTINCT processed refunds.order_id) / COUNT(DISTINCT delivered orders.id)",["orders","refunds"],["time","country","category"],"orders.order_date","percent","percent",["Order-based rate; partial refunds count once per order."]),
 _m("payment_failure_rate","Payment Failure Rate","100 * COUNT(failed payments) / COUNT(all payment attempts)",["payments"],["time","payment_method"],"payments.attempted_at","percent","percent",["Returns NULL with no attempts."]),
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
