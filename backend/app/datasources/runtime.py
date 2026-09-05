"""Build the deterministic query pipeline for one workspace's own connection.

Reuses the exact collaborators every other analytics path already goes
through -- ``PostgreSQLInspector``, ``PostgreSQLQueryValidator``,
``AnalyticsSQLExecutor`` -- rather than a parallel implementation. A
workspace connection differs only in *which* database and *which* schemas it
resolves to; read-only enforcement, SQL AST validation, and row/byte limits
are the identical code path the process-wide demo connection already uses
and already has tests for.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.analytics.connection import AnalyticsDatabase
from app.analytics.schema.allowlist import AnalyticsSchemaPolicy
from app.analytics.schema.inspector import PostgreSQLInspector
from app.analytics.sql.executor import AnalyticsSQLExecutor
from app.analytics.sql.limits import AnalyticsQueryLimits
from app.analytics.sql.validator import PostgreSQLQueryValidator
from app.datasources.contracts import DataSourceConnection, DataSourceTableCatalogEntry
from app.datasources.security import assert_safe_host, assert_safe_ssl_mode, build_dsn, build_ssl_context


@dataclass(frozen=True, slots=True)
class DataSourceRuntime:
    """The three collaborators a tool needs, scoped to one connection.

    Never cached by this module -- caching by ``data_source_id`` (and
    disposing an old runtime's engine when a connection's config changes) is
    the caller's job, since only the caller knows how long a runtime built
    from a decrypted password should stay alive.
    """

    database: AnalyticsDatabase
    inspector: PostgreSQLInspector
    validator: PostgreSQLQueryValidator
    executor: AnalyticsSQLExecutor


def build_data_source_runtime(
    connection: DataSourceConnection, *, password: str, allow_local_hosts: bool = False,
    schema_cache_ttl_seconds: float = 300,
) -> DataSourceRuntime:
    """Construct a fresh runtime for one connection.

    Re-applies the SSL-mode and SSRF checks every time, not only at
    onboarding -- a runtime is cheap to build and this is the one place nothing
    can accidentally skip the guard by reusing an old, already-checked engine.
    """

    config = connection.config
    assert_safe_ssl_mode(config.ssl_mode)
    assert_safe_host(config.host, allow_local=allow_local_hosts)

    dsn = build_dsn(config, password)
    database = AnalyticsDatabase(dsn, connect_args={
        "ssl": build_ssl_context(config.ssl_mode),
        # asyncpg's own connect() timeout -- bounds the handshake itself,
        # separate from statement_timeout_seconds which only starts once a
        # connection already exists.
        "timeout": config.connection_timeout_seconds,
    })

    policy = AnalyticsSchemaPolicy.for_schemas(config.allowed_schemas)
    inspector = PostgreSQLInspector(database, policy, cache_ttl_seconds=schema_cache_ttl_seconds)
    validator = PostgreSQLQueryValidator(policy)
    executor = AnalyticsSQLExecutor(database, AnalyticsQueryLimits(
        max_result_rows=config.max_result_rows, max_result_bytes=config.max_result_bytes,
        timeout_seconds=config.statement_timeout_seconds,
    ))
    return DataSourceRuntime(database=database, inspector=inspector, validator=validator, executor=executor)


def approved_table_names(tables: list[DataSourceTableCatalogEntry]) -> list[str]:
    """The table allowlist a governed catalog hands the validator.

    Only active tables count -- an inactive (excluded) one is invisible to
    every tool exactly as if it had never been selected, regardless of
    whether it is still sitting in the catalog for later reactivation.
    """

    return [table.technical_name for table in tables if table.active]


def explicitly_excluded_columns(tables: list[DataSourceTableCatalogEntry]) -> dict[str, frozenset[str]]:
    """The columns a human explicitly excluded -- for display, not enforcement.

    This is *not* the set query_database actually enforces: it only knows
    about columns the catalog bothered to list. Real enforcement (see
    ``app.datasources.tool_integration.build_data_source_tools``) is a
    whitelist -- every real column not in a table's approved, non-excluded
    set is blocked, including one the catalog was never told about at all.
    This function exists for API responses that want to show "what was
    explicitly turned off," which is a narrower and more human-readable
    question than "what is actually queryable."

    Deliberately keyed on ``excluded`` alone, not sensitivity: this
    application treats "sensitive" and "excluded" as two separate switches
    -- a sensitivity classification only ever blocks example-value sampling
    (enforced structurally on ``DataSourceColumnCatalogEntry`` itself), not
    querying. A workspace that wants a ``personal_data`` column queryable in
    aggregate while never sampled keeps it un-excluded; a workspace that
    wants it unreachable sets ``excluded=True`` explicitly. Profiling
    (``app.datasources.profiling``) *suggests* ``excluded=True`` by default
    for columns it classifies as ``authentication_secret``, but that is a
    default a human still approves, not a rule enforced here.
    """

    result: dict[str, frozenset[str]] = {}
    for table in tables:
        if not table.active:
            continue
        blocked = {column.technical_name for column in table.columns if column.excluded}
        if blocked:
            result[table.technical_name] = frozenset(blocked)
    return result
