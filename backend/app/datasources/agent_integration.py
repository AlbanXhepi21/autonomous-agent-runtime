"""Bridge a workspace's active data source into a live agent run.

``app.composition.providers.tools.get_tool_registry`` normally fills five
analytics tool slots (list_tables, describe_table, search_schema,
get_table_relationships, query_database) with the demo database's tools.
``resolve_workspace_tools`` builds the same five slots from a workspace's own
governed catalog instead -- the only thing a workspace-scoped agent run needs
to operate against its own connection rather than the demo one.

Metric execution is deliberately not touched here; see
``app.datasources.tool_integration`` for why.
"""

from __future__ import annotations

from uuid import UUID

from app.analytics.semantics.datasets import AnalyticsDatasetStore
from app.datasources.runtime import DataSourceRuntime
from app.datasources.service import DataSourceOnboardingService
from app.datasources.store import DataSourceStore
from app.datasources.tool_integration import build_data_source_tools
from app.tools.base import Tool


async def resolve_workspace_tools(
    *, workspace_id: UUID, service: DataSourceOnboardingService, store: DataSourceStore,
    datasets: AnalyticsDatasetStore | None = None,
) -> tuple[dict[str, Tool], DataSourceRuntime]:
    """The governed analytics tools for a workspace's one active connection.

    Returns the runtime alongside the tools so the caller can dispose its
    engine once the run finishes -- this module never closes it itself, since
    the tools must stay usable for the whole run, not just this call.
    """

    connection, runtime = await service.active_connection_runtime(workspace_id=workspace_id)
    tables = await store.list_tables(workspace_id=workspace_id, data_source_id=connection.id, active_only=True) or []
    relationships = await store.list_relationships(
        workspace_id=workspace_id, data_source_id=connection.id, approval_status="approved",
    ) or []
    tools = await build_data_source_tools(runtime, tables=tables, approved_relationships=relationships, datasets=datasets)
    return tools, runtime
