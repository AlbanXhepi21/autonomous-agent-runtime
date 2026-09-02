"""PostgreSQL AST validation for strictly read-only analytics queries."""

from collections.abc import Iterable, Mapping

import sqlglot
from sqlglot import exp

from app.analytics.schema.allowlist import AnalyticsSchemaPolicy
from app.analytics.sql.contracts import SQLValidationResult

_PROHIBITED_NODES = (
    exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Drop, exp.Alter, exp.TruncateTable,
    exp.Create, exp.Grant, exp.Revoke, exp.Command, exp.Copy, exp.Lock, exp.Into,
)
_DANGEROUS_FUNCTIONS = frozenset({
    "pg_sleep", "pg_read_file", "pg_read_binary_file", "pg_ls_dir", "pg_ls_logdir",
    "pg_stat_file", "pg_terminate_backend", "pg_cancel_backend", "dblink_connect",
    "dblink_exec", "lo_export", "lo_import", "pg_reload_conf",
})


class PostgreSQLQueryValidator:
    """Allow exactly one SELECT tree over known tables in permitted schemas."""

    def __init__(self, policy: AnalyticsSchemaPolicy) -> None:
        self._policy = policy

    def validate(
        self, sql: str, *, allowed_tables: Iterable[str],
        excluded_columns: Mapping[str, frozenset[str]] | None = None,
    ) -> SQLValidationResult:
        """Validate one read-only statement, optionally against excluded columns.

        ``excluded_columns`` maps a table name to the column names a governed
        catalog has marked off-limits (sensitive or explicitly excluded) --
        omitted entirely by every caller before this feature, so existing
        behavior for the process-wide demo connection is unchanged. A
        qualified reference (``orders.email``, or through an alias) is
        checked against that table specifically; an unqualified reference
        is checked against every referenced table's exclusions at once,
        since a validator working from syntax alone cannot always resolve
        which table an ambiguous column came from -- refusing is the safe
        direction to be wrong in, not silently allowing.
        """
        try:
            statements = sqlglot.parse(sql, read="postgres")
        except sqlglot.errors.ParseError:
            return self._invalid("SQL could not be parsed.")
        if len(statements) != 1:
            return self._invalid("Exactly one read-only SQL statement is allowed.")
        statement = statements[0]
        if not isinstance(statement, exp.Select):
            return self._invalid("Only SELECT queries and WITH ... SELECT queries are allowed.", statement)
        if any(isinstance(node, _PROHIBITED_NODES) for node in statement.walk()):
            return self._invalid("The query contains a prohibited SQL operation.", statement)
        if statement.find(exp.Lock) is not None:
            return self._invalid("Locking query clauses are not allowed.", statement)
        if self._has_dangerous_function(statement):
            return self._invalid("The query contains a prohibited database function.", statement)

        allowed = set(allowed_tables)
        cte_names = {cte.alias_or_name for cte in statement.find_all(exp.CTE)}
        tables: list[str] = []
        for table in statement.find_all(exp.Table):
            name, schema, catalog = table.name, table.db, table.catalog
            if name in cte_names and not schema and not catalog:
                continue
            if catalog or (schema and not self._policy.permits(schema)):
                return self._invalid("The query references a disallowed schema.", statement, tables)
            if not name or name not in allowed:
                return self._invalid("The query references a table that is not available for analytics.", statement, tables)
            tables.append(f"{schema}.{name}" if schema else name)

        if excluded_columns:
            issue = self._excluded_column_reference(statement, excluded_columns)
            if issue is not None:
                return self._invalid(f"The query references an excluded column: {issue}.", statement, tables)

        return SQLValidationResult(valid=True, reason="Read-only SELECT query is permitted.", statement_type="SELECT", referenced_tables=sorted(set(tables)))

    @staticmethod
    def _excluded_column_reference(
        statement: exp.Expression, excluded_columns: Mapping[str, frozenset[str]],
    ) -> str | None:
        """Return a description of the first excluded column referenced, if any."""

        alias_to_table = {table.alias_or_name: table.name for table in statement.find_all(exp.Table)}
        referenced_tables = set(alias_to_table.values())
        for column in statement.find_all(exp.Column):
            qualifier = column.table
            if qualifier:
                real_table = alias_to_table.get(qualifier, qualifier)
                if column.name in excluded_columns.get(real_table, frozenset()):
                    return f"{real_table}.{column.name}"
            else:
                for table in referenced_tables:
                    if column.name in excluded_columns.get(table, frozenset()):
                        return f"{table}.{column.name}"
        return None

    @staticmethod
    def _has_dangerous_function(statement: exp.Expression) -> bool:
        for function in statement.find_all(exp.Func):
            name = function.name.lower() if isinstance(function, exp.Anonymous) else function.sql_name().lower()
            if name in _DANGEROUS_FUNCTIONS:
                return True
        return False

    @staticmethod
    def _invalid(reason: str, statement: exp.Expression | None = None, tables: list[str] | None = None) -> SQLValidationResult:
        return SQLValidationResult(valid=False, reason=reason, statement_type=statement.key.upper() if statement else None, referenced_tables=sorted(set(tables or [])), potential_issues=[reason])
