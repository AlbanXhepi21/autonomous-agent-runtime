"""Build the analytics tool set for one workspace's approved data source.

Reuses the same tool classes the process-wide demo connection already uses
-- ``ListTablesTool``, ``DescribeTableTool``, ``SearchSchemaTool``,
``GetTableRelationshipsTool`` -- completely unchanged, fed a
``GovernedSchemaInspector`` instead of a raw one; only ``query_database``
needs a governed variant, to close the column-exclusion gap table filtering
alone cannot close (see ``app.datasources.governed_query_tool``).

Metric execution is deliberately not included here. ``MetricRegistry``'s
definitions are hand-authored SQL against the built-in demo e-commerce
schema (``orders``, ``customers``, ...) -- generalizing the semantic metric
layer itself to an arbitrary workspace schema is a materially different,
much larger undertaking than data-source onboarding, and out of scope for
this feature. Running a demo metric against a workspace's own tables would
correctly fail table validation (the referenced tables don't exist in that
connection's catalog), not silently compute the wrong numbers.
"""

from __future__ import annotations

from app.analytics.connection import AnalyticsDatabaseError
from app.analytics.schema.inspector import UnknownAnalyticsTableError
from app.analytics.semantics.datasets import AnalyticsDatasetStore
from app.datasources.contracts import DataSourceRelationship, DataSourceTableCatalogEntry
from app.datasources.governed_inspector import GovernedSchemaInspector
from app.datasources.governed_query_tool import GovernedQueryDatabaseTool
from app.datasources.runtime import DataSourceRuntime
from app.tools.base import Tool
from app.tools.database.describe_table import DescribeTableTool
from app.tools.database.list_tables import ListTablesTool
from app.tools.database.relationships import GetTableRelationshipsTool
from app.tools.database.search_schema import SearchSchemaTool


async def build_data_source_tools(
    runtime: DataSourceRuntime, *, tables: list[DataSourceTableCatalogEntry],
    approved_relationships: list[DataSourceRelationship], datasets: AnalyticsDatasetStore | None = None,
) -> dict[str, Tool]:
    """One workspace's analytics tool set, scoped to its own connection and catalog."""

    inspector = GovernedSchemaInspector(
        inspector=runtime.inspector, tables=tables, approved_relationships=approved_relationships,
    )
    query_tool = GovernedQueryDatabaseTool(
        inspector, runtime.validator, runtime.executor, await _queryable_column_whitelist(runtime, tables), datasets,
    )
    tools: list[Tool] = [
        ListTablesTool(inspector), DescribeTableTool(inspector), SearchSchemaTool(inspector),
        GetTableRelationshipsTool(inspector), query_tool,
    ]
    return {tool.name: tool for tool in tools}


async def _queryable_column_whitelist(
    runtime: DataSourceRuntime, tables: list[DataSourceTableCatalogEntry],
) -> dict[str, frozenset[str]]:
    """The excluded-column map query_database actually enforces: a whitelist.

    Every real column in the live table that is *not* in the catalog's
    approved, non-excluded set is blocked -- including one the catalog was
    never told about at all. A column absent from the catalog cannot have
    been reviewed, so it cannot be queryable; "governed" means only what was
    actually looked at is reachable, not everything that hasn't yet been
    explicitly forbidden.
    """

    result: dict[str, frozenset[str]] = {}
    for table in tables:
        if not table.active:
            continue
        allowed = {column.technical_name for column in table.columns if not column.excluded}
        try:
            description = await runtime.inspector.describe_table(table.technical_name)
        except (AnalyticsDatabaseError, UnknownAnalyticsTableError):
            continue
        blocked = {column.name for column in description.columns} - allowed
        if blocked:
            result[table.technical_name] = frozenset(blocked)
    return result
