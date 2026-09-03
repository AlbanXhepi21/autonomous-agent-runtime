"""build_data_source_tools' governed tool set, against a real restricted-role connection.

Proves the whitelist enforcement end to end: a real query against a real
column that was simply never catalogued (not just explicitly excluded) is
blocked at actual execution time, not only hidden from describe_table.
Nothing here is mocked -- the runtime is a real SSL-enabled connection
through a genuinely unprivileged PostgreSQL role.

Skips when TEST_DATABASE_URL is unset, like the other database tests.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
from pytest_asyncio import fixture
from sqlalchemy import text
from sqlalchemy.engine import make_url

pytest.importorskip("sqlalchemy")

from app.datasources.contracts import (
    DataSourceColumnCatalogEntry,
    DataSourceConnection,
    DataSourceConnectionConfig,
    DataSourceRelationship,
    DataSourceTableCatalogEntry,
)
from app.datasources.runtime import build_data_source_runtime
from app.datasources.tool_integration import build_data_source_tools
from app.db.session import Database
from app.tools.base import ToolExecutionError

pytestmark = pytest.mark.postgres

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@fixture
async def admin_dsn():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    yield TEST_DATABASE_URL


@fixture
async def restricted_role(admin_dsn):
    url = make_url(admin_dsn)
    role_name = f"datasource_tools_ro_{uuid.uuid4().hex[:12]}"
    password = "test-tools-password"
    admin = Database(admin_dsn)
    try:
        async with admin.session() as session:
            async with session.begin():
                await session.execute(text(
                    f'CREATE ROLE "{role_name}" LOGIN PASSWORD $${password}$$ '
                    "NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS"
                ))
                await session.execute(text(f'GRANT CONNECT ON DATABASE "{url.database}" TO "{role_name}"'))
                await session.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role_name}"'))
                await session.execute(text(f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{role_name}"'))
        yield url, role_name, password
    finally:
        async with admin.session() as session:
            async with session.begin():
                await session.execute(text(f'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM "{role_name}"'))
                await session.execute(text(f'REVOKE ALL ON SCHEMA public FROM "{role_name}"'))
                await session.execute(text(f'REVOKE CONNECT ON DATABASE "{url.database}" FROM "{role_name}"'))
                await session.execute(text(f'DROP ROLE "{role_name}"'))
        await admin.dispose()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _table(*, technical_name: str, columns: list[DataSourceColumnCatalogEntry]) -> DataSourceTableCatalogEntry:
    now = _now()
    return DataSourceTableCatalogEntry(
        id=uuid.uuid4(), data_source_id=uuid.uuid4(), schema_name="public", technical_name=technical_name,
        business_name=technical_name.title(), description=None, grain=None, freshness_column=None,
        active=True, approved_by="alice", approved_at=now, columns=columns, created_at=now, updated_at=now,
    )


def _column(name: str, *, excluded: bool = False, sensitivity: str = "internal") -> DataSourceColumnCatalogEntry:
    return DataSourceColumnCatalogEntry(
        id=uuid.uuid4(), table_id=uuid.uuid4(), technical_name=name, data_type="text",
        excluded=excluded, sensitivity=sensitivity,
    )


@fixture
async def runtime(restricted_role):
    url, role_name, password = restricted_role
    connection = DataSourceConnection(
        id=uuid.uuid4(), workspace_id=uuid.uuid4(), name="Tools connection",
        config=DataSourceConnectionConfig(
            host=url.host or "localhost", port=url.port or 5432, database=url.database,
            username=role_name, allowed_schemas=["public"], ssl_mode="require",
        ),
        status="verified_read_only", health_status="healthy", created_at=_now(), updated_at=_now(),
    )
    built = build_data_source_runtime(connection, password=password, allow_local_hosts=True)
    try:
        yield built
    finally:
        await built.database.dispose()


@fixture
def catalog():
    """conversations (id/title/created_at -- updated_at never catalogued) and
    messages (id/conversation_id/role/created_at -- content excluded as sensitive,
    run_id never catalogued)."""

    conversations = _table(technical_name="conversations", columns=[
        _column("id"), _column("title"), _column("created_at", sensitivity="internal"),
    ])
    messages = _table(technical_name="messages", columns=[
        _column("id"), _column("conversation_id"), _column("role"), _column("created_at"),
        _column("content", excluded=True, sensitivity="personal_data"),
    ])
    relationship = DataSourceRelationship(
        id=uuid.uuid4(), data_source_id=conversations.data_source_id, source_table="messages",
        source_column="conversation_id", target_table="conversations", target_column="id",
        cardinality="many_to_one", confidence=1.0, discovery_method="foreign_key",
        approval_status="approved", approved_by="alice", approved_at=_now(), created_at=_now(), updated_at=_now(),
    )
    return [conversations, messages], [relationship]


@pytest.mark.asyncio
async def test_list_tables_only_shows_the_catalogued_tables(runtime, catalog) -> None:
    tables, relationships = catalog
    tools = await build_data_source_tools(runtime, tables=tables, approved_relationships=relationships)

    result = await tools["list_tables"].execute()

    names = {table["name"] for table in result}
    assert names == {"conversations", "messages"}
    assert "agent_runs" not in names


@pytest.mark.asyncio
async def test_describe_table_hides_an_uncatalogued_column(runtime, catalog) -> None:
    tables, relationships = catalog
    tools = await build_data_source_tools(runtime, tables=tables, approved_relationships=relationships)

    result = await tools["describe_table"].execute(table_name="conversations")

    columns = {column["name"] for column in result["columns"]}
    assert columns == {"id", "title", "created_at"}
    assert "updated_at" not in columns


@pytest.mark.asyncio
async def test_describe_table_hides_an_explicitly_excluded_sensitive_column(runtime, catalog) -> None:
    tables, relationships = catalog
    tools = await build_data_source_tools(runtime, tables=tables, approved_relationships=relationships)

    result = await tools["describe_table"].execute(table_name="messages")

    columns = {column["name"] for column in result["columns"]}
    assert columns == {"id", "conversation_id", "role", "created_at"}
    assert "content" not in columns


@pytest.mark.asyncio
async def test_query_database_allows_a_query_against_only_catalogued_columns(runtime, catalog) -> None:
    tables, relationships = catalog
    tools = await build_data_source_tools(runtime, tables=tables, approved_relationships=relationships)

    result = await tools["query_database"].execute(sql="SELECT id, title FROM conversations LIMIT 1")

    assert [column["name"] for column in result["columns"]] == ["id", "title"]


@pytest.mark.asyncio
async def test_query_database_blocks_a_never_catalogued_column(runtime, catalog) -> None:
    """The deep whitelist gap: updated_at is a real column, just never added to the catalog."""

    tables, relationships = catalog
    tools = await build_data_source_tools(runtime, tables=tables, approved_relationships=relationships)

    with pytest.raises(ToolExecutionError):
        await tools["query_database"].execute(sql="SELECT updated_at FROM conversations LIMIT 1")


@pytest.mark.asyncio
async def test_query_database_blocks_an_explicitly_excluded_column(runtime, catalog) -> None:
    tables, relationships = catalog
    tools = await build_data_source_tools(runtime, tables=tables, approved_relationships=relationships)

    with pytest.raises(ToolExecutionError):
        await tools["query_database"].execute(sql="SELECT content FROM messages LIMIT 1")


@pytest.mark.asyncio
async def test_query_database_blocks_a_non_catalogued_table(runtime, catalog) -> None:
    tables, relationships = catalog
    tools = await build_data_source_tools(runtime, tables=tables, approved_relationships=relationships)

    with pytest.raises(ToolExecutionError):
        await tools["query_database"].execute(sql="SELECT id FROM agent_runs LIMIT 1")


@pytest.mark.asyncio
async def test_get_table_relationships_returns_only_the_approved_relationship(runtime, catalog) -> None:
    tables, relationships = catalog
    tools = await build_data_source_tools(runtime, tables=tables, approved_relationships=relationships)

    result = await tools["get_table_relationships"].execute()

    pairs = {(item["source_table"], item["target_table"]) for item in result}
    assert pairs == {("messages", "conversations")}


@pytest.mark.asyncio
async def test_search_schema_does_not_surface_an_uncatalogued_column_match(runtime, catalog) -> None:
    tables, relationships = catalog
    tools = await build_data_source_tools(runtime, tables=tables, approved_relationships=relationships)

    result = await tools["search_schema"].execute(query="updated_at")

    assert result == []
