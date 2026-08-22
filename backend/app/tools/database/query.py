"""Agent-facing, AST-validated analytics SELECT execution."""

from typing import Any

from app.analytics.connection import AnalyticsDatabaseError
from app.analytics.schema.inspector import PostgreSQLInspector
from app.analytics.semantics.datasets import AnalyticsDatasetStore
from app.analytics.sql import AnalyticsQueryError, AnalyticsSQLExecutor, PostgreSQLQueryValidator
from app.tools.base import Tool, ToolExecutionError, ToolInputError


class QueryDatabaseTool(Tool):
    """Run one validated read-only analytical query; never accept safety claims."""

    requires_run_id = True

    def __init__(self, inspector: PostgreSQLInspector, validator: PostgreSQLQueryValidator, executor: AnalyticsSQLExecutor, datasets: AnalyticsDatasetStore | None = None) -> None:
        self._inspector, self._validator, self._executor = inspector, validator, executor
        self._datasets = datasets

    @property
    def name(self) -> str: return "query_database"

    @property
    def description(self) -> str:
        return "Execute one read-only SELECT or WITH ... SELECT against approved analytics tables. SQL is independently AST-validated and result-limited."

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"sql": {"type": "string"}, "purpose": {"type": "string"}}, "required": ["sql"], "additionalProperties": False}

    async def execute(self, **arguments: Any) -> dict[str, Any]:
        return await self._execute(**arguments)

    async def execute_for_run(self, *, run_id: str | None, query_id: str, **arguments: Any) -> dict[str, Any]:
        result = await self._execute(**arguments)
        result["query_id"] = query_id
        if run_id and self._datasets is not None:
            reference = self._datasets.register(run_id=run_id, query_id=query_id,
                columns=result.get("columns", []), rows=result.get("rows", []))
            if reference is not None:
                result["dataset"] = {"id": reference.id, "row_count": reference.row_count,
                                     "byte_count": reference.byte_count, "query_id": reference.query_id}
        return result

    async def _execute(self, **arguments: Any) -> dict[str, Any]:
        sql = arguments["sql"]
        if not isinstance(sql, str) or not sql.strip():
            raise ToolInputError("SQL query must not be blank.")
        if len(sql) > 20_000:
            raise ToolInputError("SQL query must be 20,000 characters or fewer.")
        try:
            summary = await self._inspector.list_tables()
        except AnalyticsDatabaseError as error:
            raise ToolExecutionError(str(error), failure_category="database_unavailable") from error
        validation = self._validator.validate(sql, allowed_tables=[table.name for table in summary.tables])
        if not validation.valid:
            raise ToolExecutionError(validation.reason, failure_category="database_query_rejected")
        try:
            result = await self._executor.execute(sql, referenced_tables=validation.referenced_tables)
        except AnalyticsQueryError as error:
            raise ToolExecutionError(str(error), failure_category=error.failure_category) from error
        return result.model_dump()
