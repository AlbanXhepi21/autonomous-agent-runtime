"""Abstract interface for agent tools."""

from abc import ABC, abstractmethod
from typing import Any


class ToolInputError(ValueError):
    """A safe, actionable validation failure that may be returned to the agent."""


class Tool(ABC):
    """A capability the runtime may expose to the agent."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the stable name used in agent actions."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Describe when the agent should use this tool."""

    @property
    @abstractmethod
    def arguments_schema(self) -> dict[str, Any]:
        """Return a JSON-schema-like definition of accepted arguments."""

    @abstractmethod
    async def execute(self, **arguments: Any) -> Any:
        """Execute the tool and return its raw output to the executor."""
