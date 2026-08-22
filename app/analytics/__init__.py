"""Read-only, external analytics database access primitives."""

from app.analytics.connection import AnalyticsDatabase
from app.analytics.schema.inspector import PostgreSQLInspector
from app.analytics.schema.contracts import DatabaseColumn, DatabaseSchemaSummary, DatabaseTable, ForeignKeyRelationship, TableDescription
from app.analytics.presentation.findings import AnalyticalFinding

__all__ = ["AnalyticsDatabase", "PostgreSQLInspector", "AnalyticalFinding", "DatabaseColumn", "DatabaseSchemaSummary", "DatabaseTable", "ForeignKeyRelationship", "TableDescription"]
