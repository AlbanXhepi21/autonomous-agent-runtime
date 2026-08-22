"""Deterministic name-based analytics schema search."""

from typing import Any

from app.analytics.connection import AnalyticsDatabaseError
from app.analytics.schema.inspector import PostgreSQLInspector
from app.tools.base import Tool, ToolExecutionError, ToolInputError


class SearchSchemaTool(Tool):
    def __init__(self, inspector: PostgreSQLInspector) -> None: self._inspector = inspector
    @property
    def name(self) -> str: return "search_schema"
    @property
    def description(self) -> str: return "Find analytics tables by case-insensitive table or column-name matching."
    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False}
    async def execute(self, **arguments: Any) -> list[dict[str, str]]:
        try:
            return [table.model_dump(by_alias=True) for table in await self._inspector.search_schema(arguments["query"])]
        except ValueError as error:
            raise ToolInputError(str(error)) from error
        except AnalyticsDatabaseError as error:
            raise ToolExecutionError(str(error), failure_category="database_unavailable") from error
