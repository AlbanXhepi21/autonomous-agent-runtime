"""How current a connection's active data is.

Only a table an approved catalog entry marked ``active`` *and* gave a
``freshness_column`` contributes -- a table nobody has reviewed, or one
without a designated freshness column, has nothing meaningful to report, and
is silently skipped rather than treated as unknown-and-therefore-stale.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.analytics.sql.executor import AnalyticsQueryError
from app.core.logging import log_event, safe_error_message
from app.datasources.contracts import DataSourceTableCatalogEntry, FreshnessSnapshot, HealthStatus
from app.datasources.runtime import DataSourceRuntime

_logger = logging.getLogger(__name__)
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


async def compute_freshness(
    runtime: DataSourceRuntime, *, data_source_id: UUID, tables: list[DataSourceTableCatalogEntry],
    stale_after: timedelta, health_status: HealthStatus,
) -> FreshnessSnapshot:
    per_table: dict[str, datetime] = {}
    for table in tables:
        if not table.active or not table.freshness_column:
            continue
        latest = await _latest_timestamp(runtime, technical_name=table.technical_name, column_name=table.freshness_column)
        if latest is not None:
            per_table[table.technical_name] = latest

    latest_overall = max(per_table.values(), default=None)
    now = datetime.now(timezone.utc)
    stale = latest_overall is None or (now - latest_overall) > stale_after
    return FreshnessSnapshot(
        data_source_id=data_source_id, checked_at=now, latest_source_timestamp=latest_overall,
        stale=stale, health_status=health_status, per_table=per_table,
    )


async def _latest_timestamp(runtime: DataSourceRuntime, *, technical_name: str, column_name: str) -> datetime | None:
    if not (_SAFE_IDENTIFIER.match(technical_name) and _SAFE_IDENTIFIER.match(column_name)):
        return None
    sql = f'SELECT MAX("{column_name}") FROM "{technical_name}"'
    validation = runtime.validator.validate(sql, allowed_tables=[technical_name])
    if not validation.valid:
        return None
    try:
        result = await runtime.executor.execute(sql, referenced_tables=[technical_name])
    except AnalyticsQueryError as error:
        log_event(_logger, logging.WARNING, "datasource_freshness_check_failed", error=safe_error_message(error))
        return None
    if not result.rows or result.rows[0][0] is None:
        return None
    value = result.rows[0][0]
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        # The executor serializes driver values to JSON-safe types; a
        # timestamp column arrives as an ISO 8601 string, not a datetime.
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None
