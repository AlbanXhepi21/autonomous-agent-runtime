"""List permitted analytics tables without accessing table data."""

from typing import Any

from app.analytics.connection import AnalyticsDatabaseError
from app.analytics.schema.inspector import PostgreSQLInspector
from app.tools.base import Tool, ToolExecutionError


class ListTablesTool(Tool):
    def __init__(self, inspector: PostgreSQLInspector) -> None:
        self._inspector = inspector

    @property
    def name(self) -> str: return "list_tables"

    @property
    def description(self) -> str: return "List the tables available in the configured analytics schema. This returns metadata only, never table rows."

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "required": [], "additionalProperties": False}

    async def execute(self, **arguments: Any) -> list[dict[str, str]]:
        try:
            return [table.model_dump(by_alias=True) for table in (await self._inspector.list_tables()).tables]
        except AnalyticsDatabaseError as error:
            raise ToolExecutionError(str(error), failure_category="database_unavailable") from error
