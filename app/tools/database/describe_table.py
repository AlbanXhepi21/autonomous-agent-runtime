"""Describe a permitted analytics table from PostgreSQL metadata."""

from typing import Any

from app.analytics.database import AnalyticsDatabaseError
from app.analytics.inspector import PostgreSQLInspector, UnknownAnalyticsTableError
from app.tools.base import Tool, ToolExecutionError, ToolInputError


class DescribeTableTool(Tool):
    def __init__(self, inspector: PostgreSQLInspector) -> None: self._inspector = inspector
    @property
    def name(self) -> str: return "describe_table"
    @property
    def description(self) -> str: return "Describe columns, keys, and constraints for one analytics table. This returns metadata only."
    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"table_name": {"type": "string"}}, "required": ["table_name"], "additionalProperties": False}
    async def execute(self, **arguments: Any) -> dict[str, Any]:
        try:
            return (await self._inspector.describe_table(arguments["table_name"])).model_dump(by_alias=True)
        except UnknownAnalyticsTableError as error:
            raise ToolInputError(str(error)) from error
        except AnalyticsDatabaseError as error:
            raise ToolExecutionError(str(error), failure_category="database_unavailable") from error
