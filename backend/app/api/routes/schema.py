"""Read-only, safe database schema explorer endpoints.

The demo/analytics database this inspects is process-wide and pre-tenancy
(see docs/TENANCY.md, "Known limitations") -- it is not workspace-owned
data, so there is no `workspace_id` to scope these routes by. They still
require a signed-in user: this is a read surface over live schema
structure, not something to leave open to anyone on the network.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.analytics import PostgreSQLInspector
from app.analytics.schema.contracts import (
    DatabaseSchemaSummary,
    DatabaseTable,
    ForeignKeyRelationship,
    TableDescription,
)
from app.analytics.schema.inspector import UnknownAnalyticsTableError
from app.api.dependencies import get_current_user
from app.composition import get_analytics_inspector
from app.identity.contracts import User

router = APIRouter(prefix="/api/v1/schema", tags=["schema-explorer"])


# Return types are declared so these endpoints appear in the OpenAPI schema the
# Workbench generates its types from; without them the client hand-maintains
# a copy of these shapes with nothing to check it against.
@router.get("/tables")
async def list_tables(
    user: User = Depends(get_current_user), inspector: PostgreSQLInspector = Depends(get_analytics_inspector),
) -> DatabaseSchemaSummary:
    return await inspector.list_tables()


@router.get("/search")
async def search_schema(
    q: str = Query(min_length=1, max_length=120),
    user: User = Depends(get_current_user), inspector: PostgreSQLInspector = Depends(get_analytics_inspector),
) -> list[DatabaseTable]:
    return await inspector.search_schema(q)


@router.get("/tables/{table_name}")
async def describe_table(
    table_name: str,
    user: User = Depends(get_current_user), inspector: PostgreSQLInspector = Depends(get_analytics_inspector),
) -> TableDescription:
    try: return await inspector.describe_table(table_name)
    except UnknownAnalyticsTableError: raise HTTPException(status_code=404, detail={"code": "unknown_table", "message": "Table not found."})


@router.get("/tables/{table_name}/relationships")
async def table_relationships(
    table_name: str,
    user: User = Depends(get_current_user), inspector: PostgreSQLInspector = Depends(get_analytics_inspector),
) -> list[ForeignKeyRelationship]:
    try: return (await inspector.describe_table(table_name)).foreign_keys
    except UnknownAnalyticsTableError: raise HTTPException(status_code=404, detail={"code": "unknown_table", "message": "Table not found."})
