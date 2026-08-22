"""Read-only, external analytics database access primitives."""

from app.analytics.connection import AnalyticsDatabase
from app.analytics.presentation.findings import AnalyticalFinding
from app.analytics.schema.contracts import (
    DatabaseColumn,
    DatabaseSchemaSummary,
    DatabaseTable,
    ForeignKeyRelationship,
    TableDescription,
)
from app.analytics.schema.inspector import PostgreSQLInspector

__all__ = ["AnalyticsDatabase", "PostgreSQLInspector", "AnalyticalFinding", "DatabaseColumn", "DatabaseSchemaSummary", "DatabaseTable", "ForeignKeyRelationship", "TableDescription"]
