"""GovernedSchemaInspector: only the catalog's approved, active, non-excluded view.

A fake underlying inspector stands in for PostgreSQLInspector -- what's under
test here is the filtering logic itself, not real introspection (which is
already covered by the existing inspector test suite and by the integration
tests that exercise this against a real database).
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.analytics.schema.contracts import DatabaseColumn, DatabaseSchemaSummary, DatabaseTable, TableDescription
from app.analytics.schema.inspector import UnknownAnalyticsTableError
from app.datasources.contracts import DataSourceColumnCatalogEntry, DataSourceRelationship, DataSourceTableCatalogEntry
from app.datasources.governed_inspector import GovernedSchemaInspector


class FakeInspector:
    """Fixed metadata, no database -- exactly the shape GovernedSchemaInspector expects."""

    def __init__(self) -> None:
        self.tables = DatabaseSchemaSummary(
            schemas=["public"],
            tables=[DatabaseTable(name="orders", schema="public"), DatabaseTable(name="internal_audit", schema="public")],
        )
        self.descriptions = {
            "orders": TableDescription(
                name="orders", schema="public",
                columns=[
                    DatabaseColumn(name="id", data_type="uuid", nullable=False, primary_key=True),
                    DatabaseColumn(name="customer_email", data_type="text", nullable=True),
                    DatabaseColumn(name="total", data_type="numeric", nullable=False),
                ],
                primary_key=["id"], foreign_keys=[], unique_constraints=[],
            ),
        }
        self.invalidated = False

    def invalidate_cache(self) -> None:
        self.invalidated = True

    async def list_tables(self) -> DatabaseSchemaSummary:
        return self.tables

    async def describe_table(self, table_name: str) -> TableDescription:
        if table_name not in self.descriptions:
            raise UnknownAnalyticsTableError(f"Unknown table: {table_name}.")
        return self.descriptions[table_name]

    async def search_schema(self, query: str):  # pragma: no cover - not exercised via delegation anymore
        raise AssertionError("GovernedSchemaInspector must not delegate search to the raw inspector")


def _table(technical_name: str, *, active: bool = True, columns=None) -> DataSourceTableCatalogEntry:
    now = datetime.now(timezone.utc)
    return DataSourceTableCatalogEntry(
        id=uuid4(), data_source_id=uuid4(), schema_name="public", technical_name=technical_name,
        business_name=technical_name.title(), description=None, grain=None, freshness_column=None,
        active=active, approved_by=None, approved_at=None, columns=columns or [], created_at=now, updated_at=now,
    )


def _column(name: str, *, excluded: bool = False) -> DataSourceColumnCatalogEntry:
    return DataSourceColumnCatalogEntry(
        id=uuid4(), table_id=uuid4(), technical_name=name, data_type="text", excluded=excluded,
    )


@pytest.mark.asyncio
async def test_list_tables_only_returns_catalogued_active_tables() -> None:
    fake = FakeInspector()
    tables = [_table("orders")]  # "internal_audit" is never catalogued
    governed = GovernedSchemaInspector(inspector=fake, tables=tables, approved_relationships=[])

    summary = await governed.list_tables()

    assert [item.name for item in summary.tables] == ["orders"]


@pytest.mark.asyncio
async def test_an_inactive_table_is_invisible() -> None:
    fake = FakeInspector()
    tables = [_table("orders", active=False)]
    governed = GovernedSchemaInspector(inspector=fake, tables=tables, approved_relationships=[])

    summary = await governed.list_tables()

    assert summary.tables == []


@pytest.mark.asyncio
async def test_describe_table_only_shows_catalogued_columns() -> None:
    fake = FakeInspector()
    tables = [_table("orders", columns=[_column("id"), _column("total")])]  # customer_email never catalogued
    governed = GovernedSchemaInspector(inspector=fake, tables=tables, approved_relationships=[])

    description = await governed.describe_table("orders")

    assert {column.name for column in description.columns} == {"id", "total"}


@pytest.mark.asyncio
async def test_describe_table_hides_an_explicitly_excluded_column() -> None:
    fake = FakeInspector()
    tables = [_table("orders", columns=[_column("id"), _column("customer_email", excluded=True), _column("total")])]
    governed = GovernedSchemaInspector(inspector=fake, tables=tables, approved_relationships=[])

    description = await governed.describe_table("orders")

    assert {column.name for column in description.columns} == {"id", "total"}


@pytest.mark.asyncio
async def test_describe_table_refuses_an_uncatalogued_table() -> None:
    fake = FakeInspector()
    governed = GovernedSchemaInspector(inspector=fake, tables=[], approved_relationships=[])

    with pytest.raises(UnknownAnalyticsTableError):
        await governed.describe_table("orders")


@pytest.mark.asyncio
async def test_search_schema_matches_only_catalogued_columns() -> None:
    fake = FakeInspector()
    tables = [_table("orders", columns=[_column("id"), _column("total")])]
    governed = GovernedSchemaInspector(inspector=fake, tables=tables, approved_relationships=[])

    by_table_name = await governed.search_schema("orders")
    by_catalogued_column = await governed.search_schema("total")
    by_uncatalogued_column = await governed.search_schema("customer_email")

    assert [table.name for table in by_table_name] == ["orders"]
    assert [table.name for table in by_catalogued_column] == ["orders"]
    assert by_uncatalogued_column == []


@pytest.mark.asyncio
async def test_search_schema_rejects_a_blank_query() -> None:
    governed = GovernedSchemaInspector(inspector=FakeInspector(), tables=[], approved_relationships=[])

    with pytest.raises(ValueError):
        await governed.search_schema("   ")


@pytest.mark.asyncio
async def test_get_relationships_only_returns_approved_ones() -> None:
    now = datetime.now(timezone.utc)
    approved = DataSourceRelationship(
        id=uuid4(), data_source_id=uuid4(), source_table="orders", source_column="customer_id",
        target_table="customers", target_column="id", cardinality="many_to_one", confidence=1.0,
        discovery_method="foreign_key", approval_status="approved", approved_by="alice", approved_at=now,
        created_at=now, updated_at=now,
    )
    fake = FakeInspector()
    tables = [_table("orders"), _table("customers")]
    governed = GovernedSchemaInspector(inspector=fake, tables=tables, approved_relationships=[approved])

    results = await governed.get_relationships()

    assert len(results) == 1
    assert results[0].source_table == "orders" and results[0].target_table == "customers"


@pytest.mark.asyncio
async def test_get_relationships_returns_nothing_when_none_are_approved() -> None:
    """A pending, even high-confidence, relationship is never surfaced here."""

    governed = GovernedSchemaInspector(inspector=FakeInspector(), tables=[_table("orders")], approved_relationships=[])

    results = await governed.get_relationships()

    assert results == []


def test_invalidate_cache_delegates_to_the_underlying_inspector() -> None:
    fake = FakeInspector()
    governed = GovernedSchemaInspector(inspector=fake, tables=[], approved_relationships=[])

    governed.invalidate_cache()

    assert fake.invalidated is True
