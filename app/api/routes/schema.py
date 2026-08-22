"""Read-only, safe database schema explorer endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.analytics import PostgreSQLInspector
from app.analytics.inspector import UnknownAnalyticsTableError
from app.analytics.models import (
    DatabaseSchemaSummary,
    DatabaseTable,
    ForeignKeyRelationship,
    TableDescription,
)
from app.api.dependencies import get_analytics_inspector

router = APIRouter(prefix="/api/v1/schema", tags=["schema-explorer"])


# Return types are declared so these endpoints appear in the OpenAPI schema the
# Workbench generates its types from; without them the client hand-maintains
# a copy of these shapes with nothing to check it against.
@router.get("/tables")
async def list_tables(inspector: PostgreSQLInspector = Depends(get_analytics_inspector)) -> DatabaseSchemaSummary:
    return await inspector.list_tables()


@router.get("/search")
async def search_schema(q: str = Query(min_length=1, max_length=120), inspector: PostgreSQLInspector = Depends(get_analytics_inspector)) -> list[DatabaseTable]:
    return await inspector.search_schema(q)


@router.get("/tables/{table_name}")
async def describe_table(table_name: str, inspector: PostgreSQLInspector = Depends(get_analytics_inspector)) -> TableDescription:
    try: return await inspector.describe_table(table_name)
    except UnknownAnalyticsTableError: raise HTTPException(status_code=404, detail={"code": "unknown_table", "message": "Table not found."})


@router.get("/tables/{table_name}/relationships")
async def table_relationships(table_name: str, inspector: PostgreSQLInspector = Depends(get_analytics_inspector)) -> list[ForeignKeyRelationship]:
    try: return (await inspector.describe_table(table_name)).foreign_keys
    except UnknownAnalyticsTableError: raise HTTPException(status_code=404, detail={"code": "unknown_table", "message": "Table not found."})
