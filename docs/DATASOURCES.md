# Workspace PostgreSQL Data Sources

A workspace can connect its own read-only PostgreSQL analytics database and build a governed
semantic catalog on top of it, instead of only analyzing the built-in demo e-commerce database.
This is the first data source connector; only PostgreSQL is supported in this phase (no MySQL,
BigQuery, Snowflake, etc.).

The demo/global analytics stack (`app/analytics/*`, the process-wide `AnalyticsDatabase` and
`MetricRegistry`) is untouched by this feature — a workspace connection is a second, independent
instance of the same collaborators, never a shared one. See [Compatibility with the demo
database](#compatibility-with-the-demo-database).

## Setup

1. Generate a master encryption key (used to encrypt every stored data source password):

   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. Set it, and the related settings, in `backend/.env` (see `backend/.env.example`):

   ```bash
   DATA_SOURCE_ENCRYPTION_KEY=<the generated key>
   DATASOURCE_ALLOW_LOCAL_HOSTS=false   # only ever true for local development
   DATASOURCE_FRESHNESS_STALE_AFTER_HOURS=48
   ```

   No workspace can save a data source connection until `DATA_SOURCE_ENCRYPTION_KEY` is set —
   `FernetSecretCipher` refuses to construct without it. Rotating the key makes every previously
   stored password unrecoverable; there is no key history in this version, so rotation means
   re-onboarding every connection, a deliberate trade-off for a first version.

3. Apply the migration (below) and restart the API.

4. Onboard a connection through `POST /api/v1/datasources` and the steps in [Onboarding
   flow](#onboarding-flow).

## Security assumptions and controls

| Concern | Control |
| --- | --- |
| Password storage | Envelope-encrypted at rest with Fernet (AES-128-CBC + HMAC), keyed by `DATA_SOURCE_ENCRYPTION_KEY`. Only `DataSourceStore.get_encrypted_password` ever reads the ciphertext column back; every other read of a connection goes through `DataSourceConnection`, a model with no password field at all. |
| API responses | No response schema in `app/api/schemas/datasources.py` has a password field — structurally, not just by omission at each call site. |
| Connection-string logging | The password is passed through `register_secret_value` (the existing app-wide log-redaction seam) the instant it is used to build a DSN, before any connection is attempted. |
| SSRF | `assert_safe_host` resolves the configured host via DNS and refuses it if any resolved address is private, loopback, link-local, reserved, multicast, or unspecified — this explicitly covers the cloud metadata endpoint `169.254.169.254`. Re-checked on every connection build (onboarding *and* later use), not just once at setup, so a host that starts resolving internally later is still caught. Bypassable only with `DATASOURCE_ALLOW_LOCAL_HOSTS=true`, intended for local development only. |
| Unsafe SSL modes | `ssl_mode` is typed as `Literal["require", "verify-ca", "verify-full"]` at the model level — `disable`, `allow`, and `prefer` (which permit an unencrypted or silently-downgraded connection) cannot even be constructed, let alone reach a socket. |
| Read-only enforcement | Two independent checks, both required: (1) a static privilege check against `pg_roles` (`rolsuper`, `rolcreatedb`, `rolcreaterole`, `rolbypassrls`); (2) a live probe — attempt `CREATE TEMP TABLE` inside a `SET TRANSACTION READ ONLY` transaction and confirm the server actually rejects it. Every query afterward also runs inside its own `SET TRANSACTION READ ONLY` (existing `AnalyticsSQLExecutor` behavior, reused unchanged). |
| Schema/table/column access | `AnalyticsSchemaPolicy` restricts introspection and query validation to the workspace's approved schemas. `GovernedSchemaInspector` further restricts `list_tables`/`describe_table`/`search_schema` to catalog-approved, active tables and non-excluded columns — a whitelist. Query execution enforces the same whitelist independently (see [Tool integration](#tool-integration)), so a column that was simply never catalogued is blocked even though it was never explicitly excluded. |
| Cross-workspace isolation | Every store method takes `workspace_id` and filters at the query layer; a connection, table, or relationship from another workspace is indistinguishable from one that does not exist (`None` / 404), the same pattern already used by saved reports and schedules. |
| Trusted joins | A relationship discovered by `discover_relationships` (via a real foreign key, or a `<stem>_id` naming-convention heuristic) starts `approval_status="pending"` regardless of confidence. `GovernedSchemaInspector.get_relationships()` returns only `approved` relationships — an inferred join is never presented to the agent as a fact until a human approves it. |
| Example-value sampling | `DataSourceColumnCatalogEntry` structurally refuses to hold `example_values` when `sensitivity` is `personal_data`, `financial_data`, `authentication_secret`, or `restricted` (a Pydantic validator, enforced at construction, not just at the sampling call site). `sample_example_values` independently refuses to sample a sensitive column before ever running a query. |

## Migrations

`backend/migrations/versions/20260827_0009_create_data_sources.py` adds four tables, in FK
dependency order:

- **`data_sources`** — one row per workspace connection: host/port/database/username,
  `encrypted_password`, `ssl_mode`, `allowed_schemas` (JSONB array), statement timeout, row/byte
  limits, `status`, `health_status`, and connection/profiling timestamps. Indexed on
  `workspace_id` and `(workspace_id, status)`.
- **`data_source_tables`** — one row per selected table's governed metadata (business name,
  description, grain, freshness column, `active`, `approved_by`/`approved_at`). Unique on
  `(data_source_id, schema_name, technical_name)`.
- **`data_source_columns`** — one row per catalogued column (role, sensitivity, `excluded`,
  optional `example_values`). Unique on `(data_source_table_id, technical_name)`.
- **`data_source_relationships`** — one row per discovered or approved join (source/target
  table+column, cardinality, confidence, `discovery_method`, `approval_status`). Indexed on
  `(data_source_id, approval_status)`.

Apply with `alembic upgrade head` from `backend/`.

## Onboarding flow

Steps map directly onto `DataSourceOnboardingService`, and onto the API routes below:

1. **Create** — `POST /api/v1/datasources`. Encrypts the supplied password and persists the
   connection with `status="pending"`.
2. **Test connectivity** — `POST /api/v1/datasources/{id}/test-connection`. Builds a real runtime
   (re-running the SSRF/SSL guards) and runs `SELECT version()`.
3. **Verify read-only behavior** — `POST /api/v1/datasources/{id}/verify-read-only`. The two-check
   verification described above; sets `status="verified_read_only"` on success.
4. **List accessible schemas** — `GET /api/v1/datasources/{id}/schemas`.
5. **Select tables** — `POST /api/v1/datasources/{id}/tables` (also performs step 6 in the same
   call).
6. **Profile the table** — live row-count estimate (`pg_class.reltuples`, never `COUNT(*)`) and a
   name/type-based suggestion for each column's `role` and `sensitivity`
   (`app/datasources/profiling.py: suggest_role`, `suggest_sensitivity`). A column suggested
   `authentication_secret` defaults `excluded=True`.
7. **Discover candidate relationships** — `POST /api/v1/datasources/{id}/relationships/discover`.
   Foreign-key-derived candidates get confidence `1.0`; naming-convention (`<stem>_id`) candidates
   get `0.5`. Both start `pending`.
8. **Approve or correct metadata** — `PATCH /api/v1/datasources/{id}/tables/{table_id}` (correction
   resets approval), `POST .../tables/{table_id}/approve`,
   `POST .../relationships/{relationship_id}/approval`.
9. **Activate** — `POST /api/v1/datasources/{id}/activate`. Refuses unless `status ==
   "verified_read_only"` and at least one table has been approved.

## Semantic catalog

Persisted per table (`DataSourceTableCatalogEntry`): technical name, business name, description,
grain, freshness column, `active` flag, approval stamp, and its columns. Primary key, dimensions,
measures, time columns, sensitive columns, and excluded columns are all computed properties over
the column list's `role`/`sensitivity`/`excluded` fields, not separately stored — there is one
source of truth per column.

Persisted per relationship (`DataSourceRelationship`): source/target table and column,
cardinality, confidence, `discovery_method` (`foreign_key` or `inferred`), and
`approval_status` (`pending`/`approved`/`rejected`).

Sensitivity classifications: `public`, `internal`, `personal_data`, `financial_data`,
`authentication_secret`, `restricted`. A table or column is excluded from agent access via
`active=False` (table) or `excluded=True` (column) — orthogonal to sensitivity, so a
`personal_data` column can be queryable-but-never-sampled while an `authentication_secret` one is
fully excluded.

## Tool integration

`build_data_source_tools(runtime, tables=..., approved_relationships=...)` (async) builds one
workspace's own tool set:

- `list_tables`, `describe_table`, `search_schema`, `get_table_relationships` — the existing tool
  classes, unchanged, fed a `GovernedSchemaInspector` instead of the raw one.
- `query_database` — `GovernedQueryDatabaseTool`, a near-duplicate of the existing
  `QueryDatabaseTool` (not a subclass, so the demo connection's tool is untouched) that also
  threads a computed excluded-column whitelist into `PostgreSQLQueryValidator.validate(...)`.

The excluded-column set is *not* just "whatever the catalog marked excluded" — it is
`real_columns - approved_non_excluded_columns`, computed via a live `describe_table` call per
table. A column that was simply never added to the catalog is blocked exactly like one explicitly
excluded; nothing is reachable by omission.

Metric execution (`MetricRegistry`) is deliberately **not** included in the governed tool set —
its definitions are hand-authored SQL against the demo e-commerce schema, and generalizing the
semantic metric layer itself to arbitrary workspace schemas is out of scope for this phase. A
demo metric run against a workspace connection fails table validation cleanly (the referenced
tables don't exist in that connection's catalog); it does not silently compute wrong numbers.
The model never selects which connection or credentials a tool runs against — that is fixed by
whichever workspace's runtime the caller builds the tool set from.

### Wired into chat

`POST /agent/run` accepts an optional `workspace_id` on `AgentRunRequest`. When set, the run's
`list_tables`/`describe_table`/`search_schema`/`get_table_relationships`/`query_database` tools
are rebuilt from that workspace's one **active** connection (`app.datasources.agent_integration
.resolve_workspace_tools`, called from `app/api/routes/agent.py`) instead of the demo database's
tools; everything else about the run (LLM client, limits, memory, security policy) is unchanged.
A workspace with no active connection gets `400 {"code": "no_active_data_source"}` rather than a
silent fallback to the demo database. Omitted, behavior is identical to before this existed —
confirmed by the existing runtime test suite, which calls the route handler directly with its own
`AgentRunner` and needed no changes.

The connection's engine is opened for the duration of one run and disposed in a `finally` block
once it finishes; it is not pooled or cached across requests.

## Freshness

`GET /api/v1/datasources/{id}/freshness` reports: `checked_at`, `latest_source_timestamp` (the max
of every active table's configured freshness column), `stale` (against
`DATASOURCE_FRESHNESS_STALE_AFTER_HOURS`), `health_status`, and `per_table` timestamps. A table
without a configured freshness column is simply absent from `per_table`, not a null placeholder.
`last_connection_at`, `last_profiled_at`, and `health_status` are also present on the connection
resource itself (`GET /api/v1/datasources/{id}`).

## API summary

All routes are under `/api/v1/datasources`, workspace-scoped via a `workspace_id` query
parameter (default `"default"`):

| Method & path | Purpose |
| --- | --- |
| `POST /` | Create a connection (step 1) |
| `GET /` | List connections |
| `GET /{id}` | Get a connection |
| `POST /{id}/test-connection` | Step 2 |
| `POST /{id}/verify-read-only` | Step 3 |
| `GET /{id}/schemas` | Step 4 |
| `POST /{id}/activate` | Step 9 |
| `GET /{id}/freshness` | Freshness snapshot |
| `POST /{id}/tables` | Select + profile a table (steps 5–6) |
| `GET /{id}/tables`, `GET /{id}/tables/{table_id}` | List / get catalog tables |
| `PATCH /{id}/tables/{table_id}` | Correct metadata (resets approval) |
| `POST /{id}/tables/{table_id}/active` | Include/exclude a table |
| `POST /{id}/tables/{table_id}/approve` | Approve a table (step 8) |
| `POST /{id}/relationships/discover` | Step 7 |
| `GET /{id}/relationships` | List relationships (optional `approval_status` filter) |
| `POST /{id}/relationships/{relationship_id}/approval` | Approve/reject a relationship (step 8) |

A security-guard refusal (unsafe host/SSL) surfaces as `422 {"code": "connection_refused"}`,
distinct from `404 {"code": "unknown_data_source"}` for a connection that doesn't exist or isn't
visible in the caller's workspace.

## Compatibility with the demo database

Nothing under `app/analytics/*` was replaced. Three collaborators were extended
backward-compatibly, verified by both the pre-existing test suites (unmodified, still passing) and
new boundary tests:

- `AnalyticsDatabase.__init__` gained an optional `connect_args` keyword (used to inject the SSL
  context); omitted, behavior is identical to before.
- `PostgreSQLQueryValidator.validate()` gained an optional `excluded_columns` keyword; omitted
  (every existing caller — the demo `QueryDatabaseTool`, `MetricRunner`), behavior is
  byte-for-byte unchanged.
- `AnalyticsSchemaPolicy` gained `.for_schemas(...)` for a workspace's multi-schema list; the
  original single-schema `.configured(...)` is untouched.

`app.composition.providers.datasources` builds its store on `get_runtime_database()` (the
application's own database), never on `get_analytics_database()` (the demo connection's engine) —
a workspace connection's `AnalyticsDatabase`/`PostgreSQLInspector`/`PostgreSQLQueryValidator`/
`AnalyticsSQLExecutor` are always fresh instances scoped to that one connection, not shared with
the global demo singletons.

## Tests

- **Unit** (`tests/unit/datasources/`, 76 tests) — domain contract validation (sensitive columns
  can never carry examples, SSL mode can't be constructed unsafely, etc.), SSRF/SSL guard logic
  against real DNS lookups, envelope encryption round-trips and tamper detection, the governed
  inspector's whitelist logic against a fake underlying inspector, and the pure
  sensitivity/role-suggestion heuristics.
- **Integration** (`tests/integration/`, real PostgreSQL, `TEST_DATABASE_URL`-gated):
  - `test_datasource_store.py` — persistence, workspace isolation, approval-reset-on-correction,
    relationship approval state transitions.
  - `test_datasource_connectivity.py` — connectivity and read-only verification against both a
    real writable/superuser role (correctly rejected) and a real throwaway restricted role
    (correctly accepted, including surviving an actual attempted write).
  - `test_datasource_onboarding_service.py` — the full 9-step flow end to end against a real
    SSL-enabled connection, plus activation-ordering refusals, an SSRF refusal recorded as
    `status="failed"`, and cross-workspace isolation.
  - `test_datasource_tool_integration.py` — the governed tool set against a real connection,
    including the deep case: a real column that was never catalogued at all is blocked at actual
    query execution, not just hidden from `describe_table`.
- **API** (`tests/api/test_datasources_api.py`, 20 tests) — status codes and error envelopes
  against in-process fakes, including that no response ever carries a password.
- **Boundary/compatibility** (`tests/contracts/test_datasource_boundaries.py`, 20 tests) — static
  reachability checks (no `app.datasources` module can reach the LLM provider or the demo
  connection's singletons) and behavioral checks that every extended collaborator still behaves
  exactly as before when called the old way.

Run everything with `TEST_DATABASE_URL=postgresql+asyncpg://<user>:<pass>@localhost:5432/<db>
pytest -m postgres` for the database-backed suites, or plain `pytest` for unit/API/boundary tests
(the postgres-marked ones skip cleanly without `TEST_DATABASE_URL`).
