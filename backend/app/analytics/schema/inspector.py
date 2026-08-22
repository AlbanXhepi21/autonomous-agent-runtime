"""PostgreSQL metadata inspection with bounded in-process caching."""

from collections.abc import Callable
from time import monotonic
from typing import TypeVar

from sqlalchemy import inspect

from app.analytics.connection import AnalyticsDatabase, AnalyticsDatabaseError
from app.analytics.schema.allowlist import AnalyticsSchemaPolicy
from app.analytics.schema.contracts import (
    DatabaseColumn,
    DatabaseSchemaSummary,
    DatabaseTable,
    ForeignKeyRelationship,
    TableDescription,
)

T = TypeVar("T")


class UnknownAnalyticsTableError(ValueError):
    """A requested table is absent from the permitted analytics schema."""


class PostgreSQLInspector:
    """Discover real PostgreSQL metadata; never infer joins or expose comments."""

    def __init__(self, database: AnalyticsDatabase, policy: AnalyticsSchemaPolicy, *, cache_ttl_seconds: float = 300) -> None:
        self._database, self._policy = database, policy
        self._ttl = cache_ttl_seconds
        self._cache: dict[str, tuple[float, object]] = {}

    def invalidate_cache(self) -> None:
        self._cache.clear()

    async def list_tables(self) -> DatabaseSchemaSummary:
        return await self._cached("tables", self._list_tables)

    async def describe_table(self, table_name: str) -> TableDescription:
        self._validate_table_name(table_name)
        return await self._cached(f"description:{table_name}", lambda: self._describe_table(table_name))

    async def get_relationships(self, table_names: list[str] | None = None) -> list[ForeignKeyRelationship]:
        names = sorted(set(table_names or []))
        for name in names:
            self._validate_table_name(name)
        key = "relationships:" + ",".join(names)
        return await self._cached(key, lambda: self._get_relationships(names))

    async def search_schema(self, query: str) -> list[DatabaseTable]:
        query = query.strip().lower()
        if not query:
            raise ValueError("Schema search query must not be blank.")
        summary = await self.list_tables()
        matches: list[DatabaseTable] = []
        for table in summary.tables:
            description = await self.describe_table(table.name)
            if query in table.name.lower() or any(query in column.name.lower() for column in description.columns):
                matches.append(table)
        return matches

    async def _cached(self, key: str, loader: Callable[[], object]) -> T:
        cached = self._cache.get(key)
        if cached and monotonic() - cached[0] <= self._ttl:
            return cached[1]  # type: ignore[return-value]
        value = await loader()  # type: ignore[misc]
        self._cache[key] = (monotonic(), value)
        return value  # type: ignore[return-value]

    async def _list_tables(self) -> DatabaseSchemaSummary:
        async with self._database.connection() as connection:
            def load(sync_connection: object) -> DatabaseSchemaSummary:
                inspector = inspect(sync_connection)
                schemas = sorted(schema for schema in inspector.get_schema_names() if self._policy.permits(schema))
                tables = [DatabaseTable(name=name, schema=schema) for schema in schemas for name in sorted(inspector.get_table_names(schema=schema))]
                return DatabaseSchemaSummary(schemas=schemas, tables=tables)
            return await connection.run_sync(load)

    async def _describe_table(self, table_name: str) -> TableDescription:
        schema = self._single_schema()
        async with self._database.connection() as connection:
            def load(sync_connection: object) -> TableDescription:
                inspector = inspect(sync_connection)
                if table_name not in inspector.get_table_names(schema=schema):
                    raise UnknownAnalyticsTableError(f"Unknown table: {table_name}.")
                pk = set((inspector.get_pk_constraint(table_name, schema=schema) or {}).get("constrained_columns") or [])
                foreign_keys = [_relationship(table_name, schema, item) for item in inspector.get_foreign_keys(table_name, schema=schema)]
                targets = {item.source_column: f"{item.target_table}.{item.target_column}" for item in foreign_keys}
                columns = [DatabaseColumn(name=item["name"], data_type=str(item["type"]), nullable=bool(item.get("nullable", True)), primary_key=item["name"] in pk, foreign_key_target=targets.get(item["name"])) for item in inspector.get_columns(table_name, schema=schema)]
                uniques = [list(item.get("column_names") or []) for item in inspector.get_unique_constraints(table_name, schema=schema)]
                return TableDescription(name=table_name, schema=schema, columns=columns, primary_key=sorted(pk), foreign_keys=foreign_keys, unique_constraints=uniques)
            return await connection.run_sync(load)

    async def _get_relationships(self, table_names: list[str]) -> list[ForeignKeyRelationship]:
        summary = await self.list_tables()
        selected = set(table_names) if table_names else {table.name for table in summary.tables}
        relationships: list[ForeignKeyRelationship] = []
        for table in sorted(selected):
            relationships.extend((await self.describe_table(table)).foreign_keys)
        return relationships

    def _single_schema(self) -> str:
        return next(iter(self._policy.allowed_schemas))

    @staticmethod
    def _validate_table_name(table_name: str) -> None:
        if not isinstance(table_name, str) or not table_name.strip():
            raise UnknownAnalyticsTableError("Table name must not be blank.")


def _relationship(source_table: str, source_schema: str, foreign_key: dict[str, object]) -> ForeignKeyRelationship:
    columns = foreign_key.get("constrained_columns") or []
    target_columns = foreign_key.get("referred_columns") or []
    target_table = str(foreign_key.get("referred_table") or "")
    if not columns or not target_columns or not target_table:
        raise AnalyticsDatabaseError("Analytics database returned incomplete foreign-key metadata.")
    return ForeignKeyRelationship(source_table=source_table, source_column=str(columns[0]), target_table=target_table, target_column=str(target_columns[0]), source_schema=source_schema, target_schema=str(foreign_key.get("referred_schema") or source_schema))
