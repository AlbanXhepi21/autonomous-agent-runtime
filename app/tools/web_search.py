"""Placeholder interface for a future web search tool."""

from typing import Any

from app.tools.base import Tool


class WebSearchTool(Tool):
    """Reserve the interface for a future web search provider."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the public web for current information."

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        }

    async def execute(self, **arguments: Any) -> str:
        raise NotImplementedError("A web search provider has not been configured yet.")
