"""Read-only PostgreSQL execution with server and result boundaries."""

import json
from datetime import date, datetime, time
from decimal import Decimal
from time import perf_counter
from typing import Any
from uuid import UUID

from sqlalchemy import text

from app.analytics.connection import AnalyticsDatabase, AnalyticsDatabaseError
from app.analytics.sql.limits import AnalyticsQueryLimits
from app.analytics.sql.contracts import SQLColumn, SQLQueryResult


class AnalyticsQueryError(RuntimeError):
    def __init__(self, message: str, *, failure_category: str) -> None:
        super().__init__(message)
        self.failure_category = failure_category


class AnalyticsSQLExecutor:
    """Execute a validated SELECT in a PostgreSQL read-only transaction."""

    def __init__(self, database: AnalyticsDatabase, limits: AnalyticsQueryLimits) -> None:
        self._database, self._limits = database, limits

    async def execute(self, sql: str, *, referenced_tables: list[str]) -> SQLQueryResult:
        started = perf_counter()
        try:
            async with self._database.connection() as connection:
                async with connection.begin():
                    await connection.execute(text("SET TRANSACTION READ ONLY"))
                    await connection.execute(text("SELECT set_config('statement_timeout', :timeout, true)"), {"timeout": str(round(self._limits.timeout_seconds * 1000))})
                    result = await connection.stream(text(sql))
                    columns = [SQLColumn(name=key) for key in result.keys()]
                    rows, total_bytes, truncated = [], 0, False
                    while len(rows) <= self._limits.max_result_rows:
                        batch = await result.fetchmany(min(256, self._limits.max_result_rows + 1 - len(rows)))
                        if not batch:
                            break
                        for record in batch:
                            row = [_serialize_value(value) for value in record]
                            row_size = len(json.dumps(row, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8"))
                            if len(rows) >= self._limits.max_result_rows or total_bytes + row_size > self._limits.max_result_bytes:
                                truncated = True
                                break
                            rows.append(row)
                            total_bytes += row_size
                        if truncated:
                            break
                    await result.close()
        except AnalyticsDatabaseError as error:
            raise AnalyticsQueryError(str(error), failure_category="database_unavailable") from error
        except Exception as error:
            message = str(error).lower()
            if "statement timeout" in message or "query_canceled" in message:
                raise AnalyticsQueryError("Analytics query timed out.", failure_category="database_timeout") from error
            if "permission denied" in message:
                raise AnalyticsQueryError("Analytics database permission was denied.", failure_category="database_permission_denied") from error
            raise AnalyticsQueryError("Analytics query could not be executed. Check table and column names.", failure_category="database_query_error") from error
        return SQLQueryResult(columns=columns, rows=rows, row_count=len(rows), truncated=truncated, execution_ms=round((perf_counter() - started) * 1000), referenced_tables=referenced_tables)


def _serialize_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    return str(value)
