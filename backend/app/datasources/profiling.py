"""Onboarding steps 6-7: profile selected tables, discover candidate relationships.

Row counts are estimates from ``pg_class.reltuples`` -- a real ``COUNT(*)``
against a workspace's own possibly-large table is exactly the kind of
expensive scan a read-only analytics connection should not force on first
contact. Relationship discovery never invents trust: a foreign key read
straight from the catalog gets confidence 1.0 and ``discovery_method="foreign_key"``;
everything else is a naming-convention guess at confidence 0.5, and both
kinds are persisted as ``approval_status="pending"`` -- see
``app.datasources.store.create_relationship_candidates`` -- never surfaced to
the agent until a human approves them regardless of how confident the guess is.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.analytics.connection import AnalyticsDatabaseError
from app.core.logging import log_event, safe_error_message
from app.datasources.contracts import (
    SENSITIVE_CLASSIFICATIONS,
    ColumnRole,
    RelationshipCandidate,
    SensitivityClassification,
    TableProfile,
)
from app.datasources.runtime import DataSourceRuntime

_logger = logging.getLogger(__name__)

#: A bare identifier only -- table/column names reach raw SQL text below
#: (Postgres has no parameter placeholder for an identifier), so anything
#: that doesn't match this is refused before it ever reaches a query string.
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_SENSITIVE_NAME_HINTS: tuple[tuple[str, SensitivityClassification], ...] = (
    ("password", "authentication_secret"), ("secret", "authentication_secret"),
    ("api_key", "authentication_secret"), ("token", "authentication_secret"),
    ("ssn", "restricted"), ("social_security", "restricted"), ("tax_id", "restricted"),
    ("credit_card", "financial_data"), ("card_number", "financial_data"), ("cvv", "financial_data"),
    ("iban", "financial_data"), ("account_number", "financial_data"), ("salary", "financial_data"),
    ("email", "personal_data"), ("phone", "personal_data"), ("address", "personal_data"),
    ("birth", "personal_data"), ("ssn", "personal_data"),
)
_TIME_NAME_HINTS = ("_at", "_date", "_time")
_MEASURE_TYPE_HINTS = ("int", "numeric", "decimal", "double precision", "real", "float", "money")


def suggest_sensitivity(column_name: str) -> SensitivityClassification:
    """A starting-point classification a human still reviews and can correct."""

    lowered = column_name.lower()
    for hint, classification in _SENSITIVE_NAME_HINTS:
        if hint in lowered:
            return classification
    return "internal"


def suggest_role(*, name: str, data_type: str, primary_key: bool, foreign_key_target: str | None) -> ColumnRole:
    if primary_key:
        return "primary_key"
    if foreign_key_target:
        return "identifier"
    lowered = name.lower()
    if lowered.endswith(_TIME_NAME_HINTS):
        return "time"
    if lowered.endswith("_id") or lowered == "id":
        return "identifier"
    if any(hint in data_type.lower() for hint in _MEASURE_TYPE_HINTS):
        return "measure"
    return "dimension"


async def profile_table(runtime: DataSourceRuntime, *, schema_name: str, technical_name: str) -> TableProfile:
    description = await runtime.inspector.describe_table(technical_name)
    row_count = await _estimate_row_count(runtime, schema_name=schema_name, technical_name=technical_name)
    return TableProfile(
        schema_name=schema_name, technical_name=technical_name, row_count_estimate=row_count,
        columns=description.columns, profiled_at=datetime.now(timezone.utc),
    )


async def _estimate_row_count(runtime: DataSourceRuntime, *, schema_name: str, technical_name: str) -> int | None:
    try:
        async with runtime.database.connection() as connection:
            row = (await connection.execute(
                text(
                    "SELECT reltuples::bigint FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = :schema AND c.relname = :table_name"
                ),
                {"schema": schema_name, "table_name": technical_name},
            )).first()
    except (AnalyticsDatabaseError, SQLAlchemyError) as error:
        log_event(_logger, logging.WARNING, "datasource_row_estimate_failed", error=safe_error_message(error))
        return None
    if row is None or row[0] is None:
        return None
    return max(int(row[0]), 0)


async def sample_example_values(
    runtime: DataSourceRuntime, *, technical_name: str, column_name: str,
    sensitivity: SensitivityClassification, limit: int = 5,
) -> list[str]:
    """Distinct, non-null sample values for one column -- never a sensitive one.

    Goes through the exact same validate-then-execute path a hand-written
    agent query does, so sampling is bound by the connection's own row/byte
    limits and read-only enforcement rather than a separate, unaudited path.
    """

    if sensitivity in SENSITIVE_CLASSIFICATIONS:
        raise ValueError(f"Example values may not be sampled for a {sensitivity} column.")
    if not (_SAFE_IDENTIFIER.match(technical_name) and _SAFE_IDENTIFIER.match(column_name)):
        raise ValueError("Table and column names must be simple identifiers to sample from.")

    sql = (
        f'SELECT DISTINCT "{column_name}" FROM "{technical_name}" '
        f'WHERE "{column_name}" IS NOT NULL LIMIT {int(limit)}'
    )
    validation = runtime.validator.validate(sql, allowed_tables=[technical_name])
    if not validation.valid:
        raise ValueError(f"Example values could not be sampled: {validation.reason}")
    result = await runtime.executor.execute(sql, referenced_tables=[technical_name])
    return [str(row[0]) for row in result.rows if row and row[0] is not None]


_ID_SUFFIX = re.compile(r"^(?P<stem>[a-z0-9]+)_id$")


async def discover_relationships(runtime: DataSourceRuntime, *, table_names: list[str]) -> list[RelationshipCandidate]:
    """Foreign keys first (confidence 1.0), then a naming-convention guess (confidence 0.5)."""

    foreign_keys = await runtime.inspector.get_relationships(table_names)
    candidates = [
        RelationshipCandidate(
            source_table=relationship.source_table, source_column=relationship.source_column,
            target_table=relationship.target_table, target_column=relationship.target_column,
            cardinality="many_to_one", confidence=1.0, discovery_method="foreign_key",
        )
        for relationship in foreign_keys
    ]
    candidates.extend(await _infer_naming_convention_candidates(runtime, table_names, already_found=candidates))
    return candidates


async def _infer_naming_convention_candidates(
    runtime: DataSourceRuntime, table_names: list[str], *, already_found: list[RelationshipCandidate],
) -> list[RelationshipCandidate]:
    covered = {(candidate.source_table, candidate.source_column) for candidate in already_found}
    table_set = set(table_names)
    candidates: list[RelationshipCandidate] = []

    for table_name in table_names:
        description = await runtime.inspector.describe_table(table_name)
        for column in description.columns:
            if column.primary_key or column.foreign_key_target:
                continue
            match = _ID_SUFFIX.match(column.name.lower())
            if not match or (table_name, column.name) in covered:
                continue
            stem = match.group("stem")
            target_table = await _matching_table(runtime, candidates=(stem, f"{stem}s", f"{stem}es"), table_set=table_set, exclude=table_name)
            if target_table is not None:
                candidates.append(RelationshipCandidate(
                    source_table=table_name, source_column=column.name, target_table=target_table,
                    target_column="id", cardinality="many_to_one", confidence=0.5, discovery_method="inferred",
                ))
    return candidates


async def _matching_table(
    runtime: DataSourceRuntime, *, candidates: tuple[str, ...], table_set: set[str], exclude: str,
) -> str | None:
    for candidate_name in candidates:
        if candidate_name == exclude or candidate_name not in table_set:
            continue
        description = await runtime.inspector.describe_table(candidate_name)
        if "id" in {column.name.lower() for column in description.columns if column.primary_key}:
            return candidate_name
    return None
