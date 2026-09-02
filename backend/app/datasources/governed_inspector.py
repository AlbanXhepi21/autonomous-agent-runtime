"""Wrap raw introspection down to a workspace's approved semantic catalog.

Every analytics tool (``list_tables``, ``describe_table``, ``search_schema``,
``get_table_relationships``, and ``query_database`` through the allowed-table
set it derives from ``list_tables``) reaches the database through whatever
object it was constructed with -- there is no ``isinstance`` check anywhere
in that path, only calls to ``list_tables``/``describe_table``/etc. This
class stands in for a plain ``PostgreSQLInspector`` at exactly that seam: an
inactive table is simply absent from ``list_tables()``, so
``QueryDatabaseTool``'s own allowed-table computation excludes it
automatically, with no change to that tool at all. An excluded column is
stripped from ``describe_table``/``search_schema`` output, so the agent is
never even told the column exists.

Relationships are the one place this class does not delegate to raw FK
introspection at all: ``get_relationships`` returns only the workspace's
*approved* relationships (``approval_status == "approved"``), regardless of
how confidently a candidate was discovered -- an inferred join with high
confidence is still never surfaced here until a human approves it.
"""

from __future__ import annotations

from app.analytics.schema.contracts import (
    DatabaseSchemaSummary,
    DatabaseTable,
    ForeignKeyRelationship,
    TableDescription,
)
from app.analytics.schema.inspector import PostgreSQLInspector, UnknownAnalyticsTableError
from app.datasources.contracts import DataSourceRelationship, DataSourceTableCatalogEntry


class GovernedSchemaInspector:
    """Same shape as ``PostgreSQLInspector`` -- ``list_tables``, ``describe_table``,
    ``get_relationships``, ``search_schema`` -- filtered to one workspace's catalog.
    """

    def __init__(
        self, *, inspector: PostgreSQLInspector, tables: list[DataSourceTableCatalogEntry],
        approved_relationships: list[DataSourceRelationship],
    ) -> None:
        self._inspector = inspector
        self._catalog = {table.technical_name: table for table in tables if table.active}
        self._approved_relationships = approved_relationships

    def invalidate_cache(self) -> None:
        self._inspector.invalidate_cache()

    async def list_tables(self) -> DatabaseSchemaSummary:
        summary = await self._inspector.list_tables()
        return DatabaseSchemaSummary(
            schemas=summary.schemas, tables=[table for table in summary.tables if table.name in self._catalog],
        )

    async def describe_table(self, table_name: str) -> TableDescription:
        entry = self._catalog.get(table_name)
        if entry is None:
            raise UnknownAnalyticsTableError(f"{table_name!r} is not an approved analytics table.")
        description = await self._inspector.describe_table(table_name)
        # A whitelist, not a blacklist: only columns the catalog actually
        # knows about are shown, minus any of those explicitly excluded. A
        # real column the catalog was never told about (added to the table
        # after cataloging, say) must not leak through just because nobody
        # marked it excluded -- governance means "reviewed and allowed," not
        # "not yet forbidden."
        catalog_columns = {column.technical_name: column for column in entry.columns}
        return description.model_copy(update={
            "columns": [
                column for column in description.columns
                if (cataloged := catalog_columns.get(column.name)) is not None and not cataloged.excluded
            ],
        })

    async def get_relationships(self, table_names: list[str] | None = None) -> list[ForeignKeyRelationship]:
        wanted = set(table_names) if table_names else None
        results = []
        for relationship in self._approved_relationships:
            if wanted and relationship.source_table not in wanted and relationship.target_table not in wanted:
                continue
            source_schema = self._catalog.get(relationship.source_table)
            target_schema = self._catalog.get(relationship.target_table)
            results.append(ForeignKeyRelationship(
                source_table=relationship.source_table, source_column=relationship.source_column,
                target_table=relationship.target_table, target_column=relationship.target_column,
                source_schema=source_schema.schema_name if source_schema else "",
                target_schema=target_schema.schema_name if target_schema else "",
            ))
        return results

    async def search_schema(self, query: str) -> list[DatabaseTable]:
        """Match against catalog table names and *catalog* column names only.

        Deliberately does not delegate to the underlying inspector's own
        search: that would match against every real column, including ones
        this workspace never catalogued or explicitly excluded, and a table
        surfacing in search results only because of a hidden column would
        leak that the column exists even without naming it.
        """

        cleaned = query.strip().lower()
        if not cleaned:
            raise ValueError("Schema search query must not be blank.")
        summary = await self.list_tables()
        matches: list[DatabaseTable] = []
        for table in summary.tables:
            if cleaned in table.name.lower():
                matches.append(table)
                continue
            description = await self.describe_table(table.name)
            if any(cleaned in column.name.lower() for column in description.columns):
                matches.append(table)
        return matches
