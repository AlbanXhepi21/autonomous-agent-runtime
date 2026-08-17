"""Registry for the tools available to the agent runtime."""

from app.core.exceptions import UnknownToolError
from app.tools.base import Tool


class ToolRegistry:
    """Register, retrieve, and describe runtime tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Make a tool available by its stable name."""

        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        """Return a tool or raise a domain-specific lookup error."""

        try:
            return self._tools[name]
        except KeyError as error:
            raise UnknownToolError(f"Unknown tool: {name}") from error

    def definitions(self) -> list[dict[str, object]]:
        """Return tool metadata suitable for model context."""

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "arguments_schema": tool.arguments_schema,
            }
            for tool in self._tools.values()
        ]
