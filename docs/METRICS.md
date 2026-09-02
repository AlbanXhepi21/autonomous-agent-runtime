# Business Metric Reference

Generated from `app/analytics/semantics/metrics.py` by `python -m scripts.generate_metrics_doc`. Do not hand-edit: every fact below is read from the same typed `MetricDefinition` the compiler, the `/api/v1/analytics/metrics` endpoint and the agent's `describe_metric` tool all read from, so this file cannot state something the running system disagrees with.

A metric's **status** says what a reader may do with it. `documented` metrics are guidance the agent reads before writing its own SQL, which is then validated the same way as any other agent-authored query; they are never offered as something a reader may rerun by changing report parameters. `executable`, `validated` and `production_ready` metrics compile to a statement a reader may rerun directly — see `GET /api/v1/analytics/metrics`.

## Average Delivery Time

**Identifier:** `average_delivery_time:v1`  
**Status:** Validated (proven against its written definition by a fixture-based test suite)  
**Unit / format:** days (duration)

### Definition

AVG(delivered_at - shipped_at) in days, for delivered shipments

### Required tables

`shipments`, `warehouses`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- `carrier` — Carrier
- `period` — Period
- `warehouse` — Warehouse

### Allowed filters

- `carrier` — Carrier (string; operators: eq, ne, in, not_in)
- `warehouse` — Warehouse (string; operators: eq, ne, in, not_in)

### Result columns

`average_delivery_days`, `shipment_count`

### Inclusion, exclusion, null and zero-denominator behavior

- Excludes shipments with no delivered_at recorded yet.

## Average Order Value

**Identifier:** `average_order_value:v1`  
**Status:** Validated (proven against its written definition by a fixture-based test suite)  
**Unit / format:** USD (currency)

### Definition

SUM(delivered orders.total_amount) / COUNT(DISTINCT delivered orders.id)

### Required tables

`orders`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- `country` — Billing country
- `period` — Period
- `status` — Order status

### Allowed filters

- `campaign_id` — Campaign (number; operators: eq, ne, in, not_in, gt, gte, lt, lte)
- `country` — Billing country (string; operators: eq, ne, in, not_in)
- `shipping_country` — Shipping country (string; operators: eq, ne, in, not_in)

### Result columns

`total_revenue`, `order_count`, `average_order_value`

### Inclusion, exclusion, null and zero-denominator behavior

- Returns NULL when no delivered orders exist.

## Average Review Score

**Identifier:** `average_review_rating:v1`  
**Status:** Validated (proven against its written definition by a fixture-based test suite)  
**Unit / format:** stars (rating)

### Definition

AVG(reviews.rating)

### Required tables

`reviews`, `products`, `product_categories`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- `category` — Category
- `period` — Period
- `product` — Product

### Allowed filters

- `category` — Category (string; operators: eq, ne, in, not_in)
- `product` — Product (string; operators: eq, ne, in, not_in)

### Result columns

`average_rating`, `review_count`

### Inclusion, exclusion, null and zero-denominator behavior

- Reviewers are a self-selected population.

## Campaign Attributed Revenue

**Identifier:** `campaign_attributed_revenue:v1`  
**Status:** Documented (guidance only — the agent writes its own SQL)  
**Unit / format:** USD (currency)

### Definition

SUM(campaign_attribution.attributed_revenue)

### Required tables

`campaign_attribution`, `campaigns`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- _None. This metric does not support grouping by a dimension._

### Allowed filters

- _None. This metric does not support filtering._

### Result columns

_Not compiled; the agent's own query result columns apply instead._

### Inclusion, exclusion, null and zero-denominator behavior

- Uses the stored attribution model.

## Campaign ROAS

**Identifier:** `campaign_roas:v1`  
**Status:** Documented (guidance only — the agent writes its own SQL)  
**Unit / format:** ratio (number)

### Definition

SUM(attributed_revenue) / campaigns.budget

### Required tables

`campaign_attribution`, `campaigns`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- _None. This metric does not support grouping by a dimension._

### Allowed filters

- _None. This metric does not support filtering._

### Result columns

_Not compiled; the agent's own query result columns apply instead._

### Inclusion, exclusion, null and zero-denominator behavior

- Budget and attribution period alignment must be checked.

## Cancellation Rate

**Identifier:** `cancellation_rate:v1`  
**Status:** Validated (proven against its written definition by a fixture-based test suite)  
**Unit / format:** percent (percent)

### Definition

100 * COUNT(cancelled orders) / COUNT(all orders placed in the period)

### Required tables

`orders`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- `country` — Billing country
- `period` — Period
- `status` — Order status

### Allowed filters

- `campaign_id` — Campaign (number; operators: eq, ne, in, not_in, gt, gte, lt, lte)
- `country` — Billing country (string; operators: eq, ne, in, not_in)
- `shipping_country` — Shipping country (string; operators: eq, ne, in, not_in)

### Result columns

`cancelled_order_count`, `total_order_count`, `cancellation_rate_pct`

### Inclusion, exclusion, null and zero-denominator behavior

- Denominator is every order placed in the period regardless of outcome, not only delivered orders.

## Cart to Checkout Rate

**Identifier:** `cart_to_checkout_rate:v1`  
**Status:** Documented (guidance only — the agent writes its own SQL)  
**Unit / format:** percent (percent)

### Definition

100 * sessions with checkout event / sessions with cart event

### Required tables

`web_events`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- _None. This metric does not support grouping by a dimension._

### Allowed filters

- _None. This metric does not support filtering._

### Result columns

_Not compiled; the agent's own query result columns apply instead._

### Inclusion, exclusion, null and zero-denominator behavior

- Event types must be verified in the dataset.

## Checkout to Purchase Rate

**Identifier:** `checkout_to_purchase_rate:v1`  
**Status:** Documented (guidance only — the agent writes its own SQL)  
**Unit / format:** percent (percent)

### Definition

100 * sessions with purchase event / sessions with checkout event

### Required tables

`web_events`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- _None. This metric does not support grouping by a dimension._

### Allowed filters

- _None. This metric does not support filtering._

### Result columns

_Not compiled; the agent's own query result columns apply instead._

### Inclusion, exclusion, null and zero-denominator behavior

- Event types must be verified in the dataset.

## Conversion Rate

**Identifier:** `conversion_rate:v1`  
**Status:** Validated (proven against its written definition by a fixture-based test suite)  
**Unit / format:** percent (percent)

### Definition

100 * COUNT(web_sessions.converted) / COUNT(web_sessions)

### Required tables

`web_sessions`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- `channel` — Acquisition channel
- `country` — Country
- `device` — Device type
- `period` — Period

### Allowed filters

- `campaign_id` — Campaign (number; operators: eq, ne, in, not_in, gt, gte, lt, lte)
- `channel` — Acquisition channel (string; operators: eq, ne, in, not_in)
- `country` — Country (string; operators: eq, ne, in, not_in)
- `device` — Device type (string; operators: eq, ne, in, not_in)

### Result columns

`converted_session_count`, `session_count`, `conversion_rate_pct`

### Inclusion, exclusion, null and zero-denominator behavior

- converted is the session's own recorded outcome; a session may carry an order_id without being marked converted.

## Customer Count

**Identifier:** `customer_count:v1`  
**Status:** Validated (proven against its written definition by a fixture-based test suite)  
**Unit / format:** customers (number)

### Definition

COUNT(DISTINCT customer_id) with a delivered order in the period

### Required tables

`orders`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- `country` — Billing country
- `period` — Period
- `status` — Order status

### Allowed filters

- `campaign_id` — Campaign (number; operators: eq, ne, in, not_in, gt, gte, lt, lte)
- `country` — Billing country (string; operators: eq, ne, in, not_in)
- `shipping_country` — Shipping country (string; operators: eq, ne, in, not_in)

### Result columns

`customer_count`

### Inclusion, exclusion, null and zero-denominator behavior

- Counts customers active (had a delivered order) in the period, not the full customer base to date.

## Customer Lifetime Revenue

**Identifier:** `customer_lifetime_revenue:v1`  
**Status:** Documented (guidance only — the agent writes its own SQL)  
**Unit / format:** USD (currency)

### Definition

SUM(delivered orders.total_amount) per customer

### Required tables

`orders`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- _None. This metric does not support grouping by a dimension._

### Allowed filters

- _None. This metric does not support filtering._

### Result columns

_Not compiled; the agent's own query result columns apply instead._

### Inclusion, exclusion, null and zero-denominator behavior

_No stated caveats._

## Gross Margin %

**Identifier:** `gross_margin_pct:v1`  
**Status:** Validated (proven against its written definition by a fixture-based test suite)  
**Unit / format:** percent (percent)

### Definition

100 * gross_profit / SUM(order_items.line_total) for delivered orders

### Required tables

`orders`, `order_items`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- `country` — Billing country
- `period` — Period
- `status` — Order status

### Allowed filters

- `campaign_id` — Campaign (number; operators: eq, ne, in, not_in, gt, gte, lt, lte)
- `country` — Billing country (string; operators: eq, ne, in, not_in)
- `shipping_country` — Shipping country (string; operators: eq, ne, in, not_in)

### Result columns

`gross_profit`, `line_revenue`, `gross_margin_pct`

### Inclusion, exclusion, null and zero-denominator behavior

- Returns NULL when revenue denominator is zero.

## Gross Profit

**Identifier:** `gross_profit:v1`  
**Status:** Production ready (validated, and already relied on elsewhere in the system)  
**Unit / format:** USD (currency)

### Definition

SUM(order_items.line_total - order_items.unit_cost * order_items.quantity) for delivered orders

### Required tables

`orders`, `order_items`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- `country` — Billing country
- `period` — Period
- `status` — Order status

### Allowed filters

- `campaign_id` — Campaign (number; operators: eq, ne, in, not_in, gt, gte, lt, lte)
- `country` — Billing country (string; operators: eq, ne, in, not_in)
- `shipping_country` — Shipping country (string; operators: eq, ne, in, not_in)

### Result columns

`gross_profit`, `line_revenue`

### Inclusion, exclusion, null and zero-denominator behavior

_No stated caveats._

## Inventory Stockout Rate

**Identifier:** `inventory_stockout_rate:v1`  
**Status:** Documented (guidance only — the agent writes its own SQL)  
**Unit / format:** percent (percent)

### Definition

100 * COUNT(inventory rows with quantity_available <= 0) / COUNT(inventory rows)

### Required tables

`inventory`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- _None. This metric does not support grouping by a dimension._

### Allowed filters

- _None. This metric does not support filtering._

### Result columns

_Not compiled; the agent's own query result columns apply instead._

### Inclusion, exclusion, null and zero-denominator behavior

- Left documentation-only: `inventory` is a single current-state snapshot, not a period history. Every row in the seeded data shares one updated_at timestamp, so a period predicate over it would return all rows or none rather than a genuine 'stockout rate during this period'. A true period-based answer needs a dated inventory-snapshot or ledger table, which the schema does not have.
- quantity_available <= 0 never occurs in the seeded data; reorder_level-based low-stock would be the more useful current-state signal, but still cannot honestly be scoped to a reader-chosen period.

## Delayed Order Rate

**Identifier:** `late_delivery_rate:v1`  
**Status:** Validated (proven against its written definition by a fixture-based test suite)  
**Unit / format:** percent (percent)

### Definition

100 * delivered shipments after expected_delivery_at / delivered shipments

### Required tables

`shipments`, `warehouses`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- `carrier` — Carrier
- `period` — Period
- `warehouse` — Warehouse

### Allowed filters

- `carrier` — Carrier (string; operators: eq, ne, in, not_in)
- `warehouse` — Warehouse (string; operators: eq, ne, in, not_in)

### Result columns

`late_count`, `delivered_count`, `late_delivery_rate_pct`

### Inclusion, exclusion, null and zero-denominator behavior

- Excludes shipments with no delivered_at recorded yet, so an order still in transit is not counted either way.

## Net Revenue

**Identifier:** `net_revenue:v1`  
**Status:** Documented (guidance only — the agent writes its own SQL)  
**Unit / format:** USD (currency)

### Definition

SUM(delivered orders.total_amount) - SUM(processed refunds.amount)

### Required tables

`orders`, `refunds`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- _None. This metric does not support grouping by a dimension._

### Allowed filters

- _None. This metric does not support filtering._

### Result columns

_Not compiled; the agent's own query result columns apply instead._

### Inclusion, exclusion, null and zero-denominator behavior

- Refund timing may differ from order timing.

## New Customers

**Identifier:** `new_customers:v1`  
**Status:** Validated (proven against its written definition by a fixture-based test suite)  
**Unit / format:** customers (number)

### Definition

COUNT(customers) whose signup_date falls in the period

### Required tables

`customers`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- `acquisition_channel` — Acquisition channel
- `country` — Country
- `period` — Period

### Allowed filters

- `acquisition_channel` — Acquisition channel (string; operators: eq, ne, in, not_in)
- `country` — Country (string; operators: eq, ne, in, not_in)

### Result columns

`new_customer_count`

### Inclusion, exclusion, null and zero-denominator behavior

- Counts by signup date (acquisition), not by a customer's first delivered order.

## Orders

**Identifier:** `orders:v1`  
**Status:** Production ready (validated, and already relied on elsewhere in the system)  
**Unit / format:** orders (number)

### Definition

COUNT(DISTINCT delivered orders.id)

### Required tables

`orders`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- `country` — Billing country
- `period` — Period
- `status` — Order status

### Allowed filters

- `campaign_id` — Campaign (number; operators: eq, ne, in, not_in, gt, gte, lt, lte)
- `country` — Billing country (string; operators: eq, ne, in, not_in)
- `shipping_country` — Shipping country (string; operators: eq, ne, in, not_in)

### Result columns

`order_count`

### Inclusion, exclusion, null and zero-denominator behavior

_No stated caveats._

## Payment Failures

**Identifier:** `payment_failure_count:v1`  
**Status:** Production ready (validated, and already relied on elsewhere in the system)  
**Unit / format:** payments (number)

### Definition

COUNT(failed payments), optionally by method and failure reason

### Required tables

`payments`, `payment_methods`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- `failure_reason` — Failure reason
- `payment_method` — Payment method
- `period` — Period
- `provider` — Provider

### Allowed filters

- `failure_reason` — Failure reason (string; operators: eq, ne, in, not_in)
- `payment_method` — Payment method (string; operators: eq, ne, in, not_in)
- `provider` — Provider (string; operators: eq, ne, in, not_in)

### Result columns

`failure_count`, `failed_amount`

### Inclusion, exclusion, null and zero-denominator behavior

- Counts attempts, not distinct orders.

## Payment Failure Rate

**Identifier:** `payment_failure_rate:v1`  
**Status:** Documented (guidance only — the agent writes its own SQL)  
**Unit / format:** percent (percent)

### Definition

100 * COUNT(failed payments) / COUNT(all payment attempts)

### Required tables

`payments`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- _None. This metric does not support grouping by a dimension._

### Allowed filters

- _None. This metric does not support filtering._

### Result columns

_Not compiled; the agent's own query result columns apply instead._

### Inclusion, exclusion, null and zero-denominator behavior

- Returns NULL with no attempts.

## Payment Success Rate

**Identifier:** `payment_success_rate:v1`  
**Status:** Validated (proven against its written definition by a fixture-based test suite)  
**Unit / format:** percent (percent)

### Definition

100 * COUNT(completed payments) / COUNT(all payment attempts)

### Required tables

`payments`, `payment_methods`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- `payment_method` — Payment method
- `period` — Period
- `provider` — Provider

### Allowed filters

- `payment_method` — Payment method (string; operators: eq, ne, in, not_in)
- `provider` — Provider (string; operators: eq, ne, in, not_in)

### Result columns

`success_count`, `attempt_count`, `payment_success_rate_pct`

### Inclusion, exclusion, null and zero-denominator behavior

- Counts attempts, not distinct orders; complements payment_failure_count.

## Refund Rate

**Identifier:** `refund_rate:v1`  
**Status:** Validated (proven against its written definition by a fixture-based test suite)  
**Unit / format:** percent (percent)

### Definition

100 * COUNT(DISTINCT processed refunds.order_id) / COUNT(DISTINCT delivered orders.id)

### Required tables

`orders`, `refunds`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- `country` — Billing country
- `period` — Period
- `status` — Order status

### Allowed filters

- `campaign_id` — Campaign (number; operators: eq, ne, in, not_in, gt, gte, lt, lte)
- `country` — Billing country (string; operators: eq, ne, in, not_in)
- `shipping_country` — Shipping country (string; operators: eq, ne, in, not_in)

### Result columns

`refunded_order_count`, `delivered_order_count`, `refund_rate_pct`

### Inclusion, exclusion, null and zero-denominator behavior

- Order-based rate; partial refunds count once per order.
- Scoped to the order's placement date, not the refund's request date.

## Repeat Customer Rate

**Identifier:** `repeat_purchase_rate:v1`  
**Status:** Validated (proven against its written definition by a fixture-based test suite)  
**Unit / format:** percent (percent)

### Definition

100 * customers with 2+ delivered orders in the period / customers with a delivered order in the period

### Required tables

`orders`

### Supported time grains

_Not applicable._

### Allowed dimensions

- _None. This metric does not support grouping by a dimension._

### Allowed filters

- `campaign_id` — Campaign (number; operators: eq, ne, in, not_in, gt, gte, lt, lte)
- `country` — Billing country (string; operators: eq, ne, in, not_in)
- `shipping_country` — Shipping country (string; operators: eq, ne, in, not_in)

### Result columns

`repeat_customer_count`, `customer_count`, `repeat_customer_rate_pct`

### Inclusion, exclusion, null and zero-denominator behavior

- Repeat status is evaluated within the requested period, not over a customer's full history.
- No dimension breakdown: a repeat customer's orders can span more than one country or channel.

## Return Rate

**Identifier:** `return_rate:v1`  
**Status:** Documented (guidance only — the agent writes its own SQL)  
**Unit / format:** percent (percent)

### Definition

100 * physically returned units / units sold

### Required tables

`inventory_movements`, `order_items`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- _None. This metric does not support grouping by a dimension._

### Allowed filters

- _None. This metric does not support filtering._

### Result columns

_Not compiled; the agent's own query result columns apply instead._

### Inclusion, exclusion, null and zero-denominator behavior

- Left documentation-only: inventory_movements has no rows of movement_type='return' in the seeded data, and its only populated rows (movement_type='sale') all share one created_at timestamp, so it is a bulk snapshot rather than a genuine movement ledger. There is no schema-backed way to distinguish a physical product return from a refund. refund_rate is the closest honestly-supported proxy.

## Revenue

**Identifier:** `revenue:v1`  
**Status:** Production ready (validated, and already relied on elsewhere in the system)  
**Unit / format:** USD (currency)

### Definition

SUM(orders.total_amount) for delivered orders

### Required tables

`orders`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- `country` — Billing country
- `period` — Period
- `status` — Order status

### Allowed filters

- `campaign_id` — Campaign (number; operators: eq, ne, in, not_in, gt, gte, lt, lte)
- `country` — Billing country (string; operators: eq, ne, in, not_in)
- `shipping_country` — Shipping country (string; operators: eq, ne, in, not_in)

### Result columns

`revenue`, `order_count`

### Inclusion, exclusion, null and zero-denominator behavior

- Excludes cancelled and refunded orders.

## Revenue Growth

**Identifier:** `revenue_growth:v1`  
**Status:** Validated (proven against its written definition by a fixture-based test suite)  
**Unit / format:** percent (percent)

### Definition

100 * (current period revenue - prior period revenue) / prior period revenue

### Required tables

`orders`

### Supported time grains

_Not applicable._

### Allowed dimensions

- _None. This metric does not support grouping by a dimension._

### Allowed filters

- `campaign_id` — Campaign (number; operators: eq, ne, in, not_in, gt, gte, lt, lte)
- `country` — Billing country (string; operators: eq, ne, in, not_in)
- `shipping_country` — Shipping country (string; operators: eq, ne, in, not_in)

### Result columns

`current_revenue`, `prior_revenue`, `revenue_growth_pct`, `current_order_count`, `prior_order_count`

### Inclusion, exclusion, null and zero-denominator behavior

- Compares the requested period to the immediately preceding period of equal length, derived from the request's own bounds; not a calendar month-over-month or year-over-year comparison.
- No period/dimension regrouping: the metric already consumes the period as a single before/after comparison.

## Target Attainment

**Identifier:** `target_attainment:v1`  
**Status:** Production ready (validated, and already relied on elsewhere in the system)  
**Unit / format:** percent (percent)

### Definition

Delivered revenue, orders and gross profit against monthly_targets, with attainment computed in SQL

### Required tables

`orders`, `order_items`, `monthly_targets`

### Supported time grains

`month`

### Allowed dimensions

- _None. This metric does not support grouping by a dimension._

### Allowed filters

- `country` — Billing country (string; operators: eq, ne, in, not_in)

### Result columns

`period`, `revenue_actual`, `revenue_target`, `revenue_attainment_pct`, `order_actual`, `order_target`, `order_attainment_pct`, `gross_profit_actual`, `gross_profit_target`, `gross_profit_attainment_pct`

### Inclusion, exclusion, null and zero-denominator behavior

- A month with a target but no delivered orders reports a null actual.
- A month with orders but no target reports a null target and no attainment.
- A zero target yields no attainment rather than an error.
- Gross profit is joined per month and is null where no items were delivered.

## Units Sold

**Identifier:** `units_sold:v1`  
**Status:** Validated (proven against its written definition by a fixture-based test suite)  
**Unit / format:** units (number)

### Definition

SUM(order_items.quantity) for delivered orders

### Required tables

`orders`, `order_items`, `products`, `product_categories`

### Supported time grains

`day`, `week`, `month`, `quarter`, `year`

### Allowed dimensions

- `category` — Category
- `period` — Period
- `product` — Product

### Allowed filters

- `category` — Category (string; operators: eq, ne, in, not_in)
- `country` — Billing country (string; operators: eq, ne, in, not_in)
- `product` — Product (string; operators: eq, ne, in, not_in)

### Result columns

`units_sold`

### Inclusion, exclusion, null and zero-denominator behavior

_No stated caveats._
