# Adding a semantic metric

## 1. Relevant contract

`MetricDefinition` (`backend/app/analytics/semantics/metrics.py`, `extra="forbid",
frozen=True`) — the fields that matter for a new metric:

```python
name: str
version: str = "v1"
display_name: str
description: str
formula: str                       # human-readable, printed in docs/METRICS.md
grain: str
required_tables: list[str]
dimensions: list[str]
unit: str
format: Literal["currency","percent","number","duration","rating"]
business_caveats: list[str] = []
sql_template: str | None = None    # required for anything above "documented"
value_columns: tuple[str, ...] = ()
dimension_specs: dict[str, DimensionSpec] = {}
filter_specs: dict[str, FilterSpec] = {}
supported_grains: tuple[str, ...] = ("day","week","month","quarter","year")
status: MetricLifecycleStatus = "documented"
```

A model validator enforces consistency: a metric can only carry a non-`"documented"`
status if **both** `sql_template` and `value_columns` are set, and vice versa — you cannot
half-compile a metric.

## 2. Implementation location

`backend/app/analytics/semantics/metrics.py` — **there is no filesystem discovery for
metrics.** A new metric is added by appending a `MetricDefinition` (typically via the
`_m(...)` helper already used for every entry) to the module-level `DEFAULT_METRICS` list.

## 3. Registration / discovery

Adding to `DEFAULT_METRICS` *is* registration — `MetricRegistry` is a flat in-memory dict
built directly from that list at construction. Nothing else needs to be touched for the
metric to appear in `list_metrics`/`describe_metric` and the `/api/v1/analytics/metrics`
endpoint.

If you're providing a compiled definition (anything above `documented`), `sql_template` is
a **plain Python string with three literal placeholder tokens substituted via
`str.replace`** — not `.format()`, not Jinja:

```python
sql = (metric.sql_template
    .replace("{dimensions}", dimensions)
    .replace("{filters}", filters)
    .replace("{group_by}", group_by))
```

You write the raw SQL (with named bind parameters like `:period_start`) directly as a
module-level string constant in `metrics.py`, referencing it via `sql_template=_YOUR_SQL`.
Every `DimensionSpec.expression` and `FilterSpec.column` must match a restrictive
"safe expression" regex in `compiler.py`, or compilation raises `MetricCompilationError`.

## 4. Security or capability requirements

None beyond what already applies to `query_database` — a compiled metric's SQL is
re-validated through **the exact same `PostgreSQLQueryValidator`** used for agent-written
SQL before it ever runs (see
[data-analysis.md](../architecture/data-analysis.md#semantic-metric-execution)). There is
no separate or lighter trust path for metric SQL just because you wrote it by hand instead
of the agent.

## 5. Tests required

Two distinct tiers, because they prove different things — **do not skip the second tier
and call the metric `validated`**:

1. **Compilation/structure** — `backend/tests/unit/analytics/test_metric_compilation.py`:
   compiles your metric with `compile_metric()` against the real `MetricRegistry()`, then
   runs the resulting SQL text through `PostgreSQLQueryValidator` (AST-only, **no live
   database**). This proves the SQL is well-formed and safe, not that it computes the
   right number.
2. **Arithmetic correctness** — `backend/tests/integration/test_metric_reruns.py` (or a
   `_group1`/`_group2` sibling): runs the compiled statement against a real Postgres
   fixture database via `MetricRunner` and asserts the actual numbers. Marked `postgres`,
   skipped when `ANALYTICS_DATABASE_URL` is unset. The module's own docstring states the
   reason plainly: *"Compilation can be checked without a database; arithmetic cannot."*

Only after both pass should a metric be given `validated` (or, if something else in the
system already depends on it, `production_ready`) status.

## 6. Documentation required

Run the generator — do not hand-edit `docs/METRICS.md`:

```bash
cd backend && .venv/bin/python -m scripts.generate_metrics_doc
```

A contract test (`backend/tests/contracts/test_metrics_doc_snapshot.py`) fails the whole
suite if `metrics.py` changes without this being run — it re-renders the markdown from the
live registry and asserts string equality against the committed file, with the exact
failure message *"A metric definition changed but docs/METRICS.md was not regenerated."*
Also update the summary table in
[semantic-metrics.md](../concepts/semantic-metrics.md) by hand — that page is not
auto-generated.

## 7. Common mistakes

- Setting `status="validated"` before the integration-tier test exists — the compilation
  test alone cannot catch a metric that's syntactically valid but arithmetically wrong
  (e.g., double-counting a join fan-out).
- Forgetting to regenerate `docs/METRICS.md` — this is not a soft reminder, it's a hard
  CI-equivalent test failure (`test_metrics_doc_snapshot.py`).
- Writing a `DimensionSpec.expression` or `FilterSpec.column` that doesn't match the safe
  expression pattern the compiler enforces — you'll get a clear
  `MetricCompilationError`, not a silent SQL injection risk, but it can be non-obvious
  which character tripped the regex on first attempt.
- Leaving `status="documented"` on a metric that actually has `sql_template` and
  `value_columns` set — the model validator rejects this combination outright, so this
  fails fast rather than shipping inconsistently, but it's worth knowing the two must
  move together.
- Assuming a metric works against workspace-connected data sources — semantic metrics
  today only run against the fixed demo schema (see
  [limitations.md](../reference/limitations.md)).

## 8. Complete minimal example

A `documented`-only metric (no compiled SQL — the safer, simpler starting point):

```python
# in DEFAULT_METRICS, backend/app/analytics/semantics/metrics.py
_m(
    name="wishlist_conversion_rate",
    display_name="Wishlist Conversion Rate",
    description="Share of wishlisted products later purchased.",
    formula="100 * wishlisted products later purchased / wishlisted products",
    grain="day",
    required_tables=["wishlists", "order_items"],
    dimensions=[],
    unit="percent",
    format="percent",
    business_caveats=[
        "No schema-backed link between a wishlist entry and the order that fulfilled it "
        "yet — treat this as agent-written-SQL guidance only.",
    ],
    # status defaults to "documented"; no sql_template/value_columns needed
)
```

Then:

```bash
cd backend && .venv/bin/python -m scripts.generate_metrics_doc
cd backend && .venv/bin/python -m pytest tests/contracts/test_metrics_doc_snapshot.py
```

Promoting this to `validated` later requires adding `sql_template`, `value_columns`,
`dimension_specs`/`filter_specs` as needed, a compilation test, and an integration test
against a real database — see [semantic-metrics.md](../concepts/semantic-metrics.md) for
what a fully compiled metric definition looks like in practice.
