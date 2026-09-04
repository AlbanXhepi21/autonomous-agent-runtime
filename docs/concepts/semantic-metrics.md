# Semantic metrics

This page is a compact index over every registered metric, built from
[`backend/app/analytics/semantics/metrics.py`](../../backend/app/analytics/semantics/metrics.py).
**[`../METRICS.md`](../METRICS.md) is the canonical, machine-generated reference** — it is
regenerated directly from the same `MetricDefinition` objects by
`python -m scripts.generate_metrics_doc` (see [commands.md](../reference/commands.md)) and
kept in sync with a contract test, so it cannot state something the running system
disagrees with. If this page and `METRICS.md` ever appear to disagree, `METRICS.md` (or
regenerating it) is authoritative. Full prose definitions, dimension/filter descriptions,
and complete null/zero-behavior caveats for every metric live there; this page exists to
answer "what's the status of metric X" and "which metrics are actually executable" at a
glance.

## Lifecycle statuses

A metric's status governs what a caller may do with it, not just how trustworthy it is:

| Status | Meaning |
|---|---|
| `documented` | Guidance only. No compiled SQL exists — the agent writes its own query, which is validated exactly like any other agent-authored SQL (see [data-analysis.md](../architecture/data-analysis.md)). Never offered as something a reader can rerun by changing parameters. |
| `executable` | Compiles to a statement — currently **no metric holds this status**; it exists as an intermediate step before `validated`. |
| `validated` | Compiles to a statement, proven against its written definition by a fixture-based test suite. Rerunnable with different parameters. |
| `production_ready` | Validated, and already relied on elsewhere in the system. Rerunnable with different parameters. |

**Do not label a metric "executable" in any other document unless it genuinely has both a
compiled SQL definition and a passing test proving that definition correct** — of the 28
metrics registered today, 19 compile to SQL (`validated` or `production_ready`) and 9 are
`documented`-only; none currently sits at the bare `executable` status.

A `validated`/`production_ready`/`executable` metric's compiled SQL is re-validated through
the **same** `PostgreSQLQueryValidator` used for agent-written SQL before it ever runs — a
compiled statement gets no special trust (see
[data-analysis.md](../architecture/data-analysis.md#semantic-metric-execution)).

## All 28 metrics

| ID | Label | Status | Executable? | Grain | Dimensions | Filters | Required tables |
|---|---|---|---|---|---|---|---|
| `revenue:v1` | Revenue | production_ready | Yes | day–year | country, period, status | campaign_id, country, shipping_country | orders |
| `gross_profit:v1` | Gross Profit | production_ready | Yes | day–year | country, period, status | campaign_id, country, shipping_country | orders, order_items |
| `orders:v1` | Orders | production_ready | Yes | day–year | country, period, status | campaign_id, country, shipping_country | orders |
| `payment_failure_count:v1` | Payment Failures | production_ready | Yes | day–year | failure_reason, payment_method, period, provider | failure_reason, payment_method, provider | payments, payment_methods |
| `target_attainment:v1` | Target Attainment | production_ready | Yes | month | *(none)* | country | orders, order_items, monthly_targets |
| `average_delivery_time:v1` | Average Delivery Time | validated | Yes | day–year | carrier, period, warehouse | carrier, warehouse | shipments, warehouses |
| `average_order_value:v1` | Average Order Value | validated | Yes | day–year | country, period, status | campaign_id, country, shipping_country | orders |
| `average_review_rating:v1` | Average Review Score | validated | Yes | day–year | category, period, product | category, product | reviews, products, product_categories |
| `cancellation_rate:v1` | Cancellation Rate | validated | Yes | day–year | country, period, status | campaign_id, country, shipping_country | orders |
| `conversion_rate:v1` | Conversion Rate | validated | Yes | day–year | channel, country, device, period | campaign_id, channel, country, device | web_sessions |
| `customer_count:v1` | Customer Count | validated | Yes | day–year | country, period, status | campaign_id, country, shipping_country | orders |
| `gross_margin_pct:v1` | Gross Margin % | validated | Yes | day–year | country, period, status | campaign_id, country, shipping_country | orders, order_items |
| `late_delivery_rate:v1` | Delayed Order Rate | validated | Yes | day–year | carrier, period, warehouse | carrier, warehouse | shipments, warehouses |
| `new_customers:v1` | New Customers | validated | Yes | day–year | acquisition_channel, country, period | acquisition_channel, country | customers |
| `payment_success_rate:v1` | Payment Success Rate | validated | Yes | day–year | payment_method, period, provider | payment_method, provider | payments, payment_methods |
| `refund_rate:v1` | Refund Rate | validated | Yes | day–year | country, period, status | campaign_id, country, shipping_country | orders, refunds |
| `repeat_purchase_rate:v1` | Repeat Customer Rate | validated | Yes | not applicable | *(none)* | campaign_id, country, shipping_country | orders |
| `revenue_growth:v1` | Revenue Growth | validated | Yes | not applicable | *(none)* | campaign_id, country, shipping_country | orders |
| `units_sold:v1` | Units Sold | validated | Yes | day–year | category, period, product | category, country, product | orders, order_items, products, product_categories |
| `campaign_attributed_revenue:v1` | Campaign Attributed Revenue | documented | No — agent writes SQL | day–year | *(none)* | *(none)* | campaign_attribution, campaigns |
| `campaign_roas:v1` | Campaign ROAS | documented | No — agent writes SQL | day–year | *(none)* | *(none)* | campaign_attribution, campaigns |
| `cart_to_checkout_rate:v1` | Cart to Checkout Rate | documented | No — agent writes SQL | day–year | *(none)* | *(none)* | web_events |
| `checkout_to_purchase_rate:v1` | Checkout to Purchase Rate | documented | No — agent writes SQL | day–year | *(none)* | *(none)* | web_events |
| `customer_lifetime_revenue:v1` | Customer Lifetime Revenue | documented | No — agent writes SQL | day–year | *(none)* | *(none)* | orders |
| `inventory_stockout_rate:v1` | Inventory Stockout Rate | documented | No — agent writes SQL | day–year | *(none)* | *(none)* | inventory |
| `net_revenue:v1` | Net Revenue | documented | No — agent writes SQL | day–year | *(none)* | *(none)* | orders, refunds |
| `payment_failure_rate:v1` | Payment Failure Rate | documented | No — agent writes SQL | day–year | *(none)* | *(none)* | payments |
| `return_rate:v1` | Return Rate | documented | No — agent writes SQL | day–year | *(none)* | *(none)* | inventory_movements, order_items |

## Business definitions and null/zero behavior (condensed)

Full prose lives in [`../METRICS.md`](../METRICS.md); condensed here for quick reference.

- **revenue** — `SUM(orders.total_amount)` for delivered orders. Excludes cancelled and refunded orders.
- **gross_profit** — `SUM(line_total − unit_cost×quantity)` for delivered orders. No stated caveats.
- **orders** — `COUNT(DISTINCT delivered orders.id)`. No stated caveats.
- **payment_failure_count** — `COUNT(failed payments)`, optionally by method/reason. Counts attempts, not distinct orders.
- **target_attainment** — Delivered revenue/orders/gross profit against `monthly_targets`. A month with a target but no orders reports a null actual; a zero target yields no attainment rather than an error.
- **average_delivery_time** — `AVG(delivered_at − shipped_at)` in days. Excludes shipments not yet delivered.
- **average_order_value** — `SUM(total_amount) / COUNT(DISTINCT id)` for delivered orders. NULL when no delivered orders exist.
- **average_review_rating** — `AVG(rating)`. Reviewers are a self-selected population.
- **cancellation_rate** — `100 × cancelled / all orders placed`. Denominator is every order placed, not only delivered ones.
- **conversion_rate** — `100 × converted sessions / sessions`. "Converted" is the session's own recorded outcome.
- **customer_count** — Distinct customers with a delivered order in the period, not the full customer base to date.
- **gross_margin_pct** — `100 × gross_profit / line revenue`. NULL when the revenue denominator is zero.
- **late_delivery_rate** — `100 × delivered-after-expected / delivered`. Excludes shipments not yet delivered.
- **new_customers** — Counted by signup date, not by a customer's first delivered order.
- **payment_success_rate** — `100 × completed / all attempts`. Counts attempts, not distinct orders.
- **refund_rate** — `100 × DISTINCT refunded orders / DISTINCT delivered orders`. Partial refunds count once per order; scoped to order placement date, not refund date.
- **repeat_purchase_rate** — `100 × customers with 2+ delivered orders / customers with a delivered order`, evaluated within the requested period only, not lifetime.
- **revenue_growth** — `100 × (current − prior) / prior`, comparing to the immediately preceding period of equal length — not a calendar month/year comparison.
- **units_sold** — `SUM(quantity)` for delivered orders. No stated caveats.
- **campaign_attributed_revenue** — `SUM(attributed_revenue)`. Uses the stored attribution model.
- **campaign_roas** — `SUM(attributed_revenue) / budget`. Budget/attribution period alignment must be checked by whoever writes the query.
- **cart_to_checkout_rate** / **checkout_to_purchase_rate** — funnel ratios over `web_events`; event types must be verified in the dataset before use.
- **customer_lifetime_revenue** — `SUM(total_amount)` per customer. No stated caveats.
- **inventory_stockout_rate** — Left documentation-only: `inventory` is a single current-state snapshot, not a period history, so a period predicate over it is not honestly answerable; no row in the seed data even has `quantity_available ≤ 0`.
- **net_revenue** — `SUM(delivered orders) − SUM(processed refunds)`. Refund timing may differ from order timing.
- **payment_failure_rate** — `100 × failed / all attempts`. NULL with no attempts.
- **return_rate** — Left documentation-only: no schema-backed way to distinguish a physical return from a refund; `refund_rate` is the closest honestly-supported proxy.

## Known limitations

- 9 of 28 metrics are documentation-only by design — the underlying schema cannot honestly
  support a compiled, period-scoped definition for them today (most commonly because a
  table is a current-state snapshot rather than a dated history).
- No metric currently sits at the `executable` status — it exists in the lifecycle as an
  intermediate step but nothing occupies it today.
- Semantic metrics (and therefore parameterized reruns) are not available against
  workspace-connected data sources — only the fixed demo schema.
