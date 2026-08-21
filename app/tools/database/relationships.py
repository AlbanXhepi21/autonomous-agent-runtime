"""Read direct foreign-key relationships from analytics metadata."""

from typing import Any

from app.analytics.database import AnalyticsDatabaseError
from app.analytics.inspector import PostgreSQLInspector, UnknownAnalyticsTableError
from app.tools.base import Tool, ToolExecutionError, ToolInputError


class GetTableRelationshipsTool(Tool):
    def __init__(self, inspector: PostgreSQLInspector) -> None: self._inspector = inspector
    @property
    def name(self) -> str: return "get_table_relationships"
    @property
    def description(self) -> str: return "Return direct foreign-key relationships for one or more analytics tables; never guess joins."
    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"table_name": {"type": "string"}, "table_names": {"type": "array", "items": {"type": "string"}}}, "required": [], "additionalProperties": False}
    async def execute(self, **arguments: Any) -> list[dict[str, Any]]:
        single, many = arguments.get("table_name"), arguments.get("table_names")
        if single is not None and many is not None:
            raise ToolInputError("Provide either table_name or table_names, not both.")
        names = [single] if single is not None else many
        if names is not None and (not isinstance(names, list) or not all(isinstance(name, str) for name in names)):
            raise ToolInputError("table_names must be an array of table names.")
        try:
            return [item.model_dump(by_alias=True) for item in await self._inspector.get_relationships(names)]
        except UnknownAnalyticsTableError as error:
            raise ToolInputError(str(error)) from error
        except AnalyticsDatabaseError as error:
            raise ToolExecutionError(str(error), failure_category="database_unavailable") from error
