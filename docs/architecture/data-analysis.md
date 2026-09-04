# Data analysis

This document covers `backend/app/analytics/` — schema discovery, SQL validation and
execution, result handling, and semantic metrics. Every enforcement claim below is tied to
either the enforcing code or a test that exercises it; where a claim could not be verified
against an actual check or test, that's stated explicitly rather than assumed.

## Schema discovery

`PostgreSQLInspector` (`backend/app/analytics/schema/inspector.py`) discovers tables and
columns through SQLAlchemy's `inspect()` reflection API (`get_schema_names`,
`get_table_names`, `get_columns`, `get_foreign_keys`, ...) — it never composes raw SQL
itself for discovery. This makes discovery safe by construction rather than by reuse of
the query validator: reflection methods only ever read catalog metadata, so there is no
injection surface to validate. Discovery results are cached in-process with a TTL
(`ANALYTICS_SCHEMA_CACHE_TTL_SECONDS`, default 300s).

For workspace-connected data sources, `GovernedSchemaInspector`
(`backend/app/datasources/governed_inspector.py`) wraps the same class and filters its
results down to the workspace's approved, non-excluded catalog before anything reaches
the agent — see [Schema allowlisting](#schema-allowlisting-and-column-governance).

## SQL generation

The agent writes SQL itself. `query_database`'s argument schema
(`backend/app/tools/database/query.py`) requires a `sql: str` field — there is no
structured query-builder standing between the model and the database; every query is raw
text that then passes through the validation described below before it can run.

## Read-only database access

Read-only is enforced **per query, at the SQL-transaction level**:
`AnalyticsSQLExecutor.execute()` (`backend/app/analytics/sql/executor.py`) issues
`SET TRANSACTION READ ONLY` and sets a transaction-local `statement_timeout` before
running the caller's SQL. This applies to every query that goes through the executor,
which every analytics tool does.

For **workspace-connected** data sources, there is a second, independent layer: onboarding
requires `verify_read_only()` (`backend/app/datasources/connectivity.py`), which checks
the connecting role's PostgreSQL privileges (`rolsuper`/`rolcreatedb`/`rolcreaterole`/
`rolbypassrls`) *and* live-probes that PostgreSQL itself rejects a write inside a
`SET TRANSACTION READ ONLY` block — a connection cannot be activated until this passes.
This is tested against a genuinely restricted database role
(`backend/tests/integration/test_datasource_connectivity.py`).

**For the process-wide demo database** (`ANALYTICS_DATABASE_URL`), no equivalent
role-level check exists — verified by the absence of any call to `verify_read_only` or a
`pg_roles` check outside the workspace data-source onboarding path. Read-only for the demo
connection rests entirely on the transaction-level `SET TRANSACTION READ ONLY` applied by
the executor. This is a real, current gap, not merely an undocumented one: if the
configured demo role has write privileges and some future code path opened a connection
without routing through `AnalyticsSQLExecutor`, nothing would stop a write. Every existing
analytics tool does route through the executor today.

## sqlglot AST validation

`PostgreSQLQueryValidator` (`backend/app/analytics/sql/validator.py`) parses submitted SQL
with `sqlglot` (`postgres` dialect) and rejects it unless all of the following hold:

- Exactly one statement (multi-statement input, e.g. `SELECT ...; DELETE ...`, is
  rejected).
- The single statement is a `SELECT` (a `WITH ... SELECT` common-table-expression counts,
  since sqlglot parses it as a `Select` node with CTE children).
- It contains none of a fixed set of prohibited node types: `INSERT`, `UPDATE`, `DELETE`,
  `MERGE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE`, a generic `COMMAND`
  node (catching things like `CALL` or `DO $$...$$`), `COPY`, `LOCK`, and `SELECT ... INTO`.
- It contains none of a fixed dangerous-function blocklist: `pg_sleep`,
  `pg_read_file`/`pg_read_binary_file`, `pg_ls_dir`/`pg_ls_logdir`, `pg_stat_file`,
  `pg_terminate_backend`/`pg_cancel_backend`, `dblink_connect`/`dblink_exec`,
  `lo_export`/`lo_import`, `pg_reload_conf` — checked case-insensitively against both
  named and generic function-call forms.
- Every referenced table resolves to an allowed schema and an allowed table name (see
  below); every referenced column, if a column-exclusion set was supplied, is not
  excluded.

## Schema allowlisting and column governance

Three independent layers, each doing a different job:

1. **Schema allowlist** (`AnalyticsSchemaPolicy`,
   `backend/app/analytics/schema/allowlist.py`) — a schema is queryable only if it's
   explicitly listed; nothing is queryable by default.
2. **Table allowlist** — computed per call from whatever the (possibly governed) inspector
   currently reports as available, and passed into the validator; for workspace sources
   this list is already filtered to the approved, active catalog before validation ever
   sees it.
3. **Column exclusion, a whitelist inverted into a blocklist** — for workspace sources,
   `_queryable_column_whitelist` (`backend/app/datasources/tool_integration.py`) computes
   "every real column not in the catalog's approved, non-excluded set" and passes that as
   the validator's excluded-columns argument — deliberately including a column the catalog
   was never told about at all, not only ones an operator explicitly marked excluded.

**Sensitivity classification does not feed the validator.** A column's
`SensitivityClassification` (e.g. "authentication_secret," "personal_data") gates only
whether *example values* may be sampled during profiling — it has no effect on whether the
column can be queried. The only thing the validator ever sees is the boolean `excluded`
flag. The one link between the two: profiling *suggests* `excluded=True` for a column
classified `authentication_secret`, but that suggestion still requires a human's approval
before it takes effect. Documentation or expectations that a sensitivity tier is enforced
at query time would be incorrect.

## Prohibited SQL — test coverage

The rejection behavior above is exercised by
`backend/tests/unit/analytics/test_analytics_sql.py`: accepted cases (plain `SELECT`,
joins, `WITH` CTEs, window functions), and rejected cases (every DML/DDL statement type,
stacked statements, a mutating CTE, `pg_catalog`/`information_schema` references,
`pg_sleep`, `FOR UPDATE`, `SELECT ... INTO`). Row/byte-limit enforcement and the `READ
ONLY` transaction are asserted directly against a fake connection's executed statements.

**Column-exclusion rejection is proven only by an integration test against a real
PostgreSQL database** (`backend/tests/integration/test_datasource_tool_integration.py`,
marked `postgres` and skipped when `TEST_DATABASE_URL` is unset) — the pure unit tests for
the validator do not exercise the excluded-columns parameter at all. Treat
"column exclusion is test-enforced" as true but conditional on that integration suite
actually running.

## Timeouts, row limits, and byte limits

All three are configuration-driven (`ANALYTICS_QUERY_TIMEOUT_SECONDS`,
`ANALYTICS_MAX_RESULT_ROWS`, `ANALYTICS_MAX_RESULT_BYTES` — see
[configuration.md](../getting-started/configuration.md)) and applied inside
`AnalyticsSQLExecutor.execute()`:

- **Timeout** is enforced by PostgreSQL itself, not application-level `asyncio` timeout —
  the executor sets a transaction-local `statement_timeout` and PostgreSQL cancels the
  statement server-side if it's exceeded.
- **Row and byte limits are enforced while streaming, not after a full fetch.** Results
  are pulled in bounded batches; each row's serialized size is counted as it arrives, and
  the stream is cut the moment either the row count or the accumulated byte count would
  exceed its limit — a query that would return an enormous result set never has that
  result set fully materialized in the first place.

## Result storage

`AnalyticsDatasetStore` (`backend/app/analytics/semantics/datasets.py`) is a
**pure in-memory, in-process dictionary**, keyed by run ID and dataset ID, with no
persistence and no automatic time-based expiry — it enforces only size caps at write time
(dropping registration silently if a result exceeds the configured row/byte cap for
Python-based analysis). It provides a `clear_run()` method to remove all datasets for a
run, but this documentation could not confirm, from the analytics package alone, that
run-completion code actually calls it — treat "results are cleared at the end of a run" as
supported by the store's design, not confirmed as wired up end-to-end.

`query_database` registers its result into this store immediately after execution; the
sandboxed `analyze_dataset` tool later retrieves it by ID to run restricted Python over the
same rows (see [security-boundaries.md](security-boundaries.md) for the sandbox itself).

## Semantic metric execution

A `MetricDefinition` (`backend/app/analytics/semantics/metrics.py`) compiles to SQL via
`compile_metric()`, and that compiled SQL is passed through **the same
`PostgreSQLQueryValidator` instance** used for agent-written SQL — not a separate or
lighter path. The module's own comment states the intent plainly: a compiled statement is
not exempt, and if the compiler and validator ever disagreed, the validator wins and
nothing runs. Execution then goes through the same `AnalyticsSQLExecutor`, with compiled
parameters bound rather than string-interpolated.

Metrics carry one of four lifecycle statuses
(`documented`, `executable`, `validated`, `production_ready`); of the 28 metrics shipped
today, 9 are `documented` only (no compiled SQL — the agent must write its own query for
these), 14 are `validated`, and 5 are `production_ready`. `executable` currently has no
members. The full list, with identifiers, required tables, and status, is machine-generated
into [`../METRICS.md`](../METRICS.md) directly from this file — do not hand-maintain a
second copy of it.

Semantic metrics are deliberately not available against workspace-connected data sources
today — they are authored against the fixed demo schema only.

## Known limitations

- The process-wide demo analytics connection has no role-level read-only verification,
  unlike workspace-connected sources — see
  [Read-only database access](#read-only-database-access).
- Column-exclusion enforcement is proven only by a database-dependent integration test,
  not by the default unit-test run.
- `AnalyticsDatasetStore`'s per-run cleanup method exists but its call site during normal
  run completion was not located in this pass.
- Sensitivity classification is a profiling/sampling concept only; it does not restrict
  what can be queried.
