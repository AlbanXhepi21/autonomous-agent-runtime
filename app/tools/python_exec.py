"""Placeholder interface for a future sandboxed Python execution tool."""

from typing import Any

from app.tools.base import Tool


class PythonExecTool(Tool):
    """Reserve the interface for Python execution pending sandboxing."""

    @property
    def name(self) -> str:
        return "python_exec"

    @property
    def description(self) -> str:
        return "Run Python code in a future sandboxed environment."

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
            "additionalProperties": False,
        }

    async def execute(self, **arguments: Any) -> str:
        raise NotImplementedError("Python execution requires sandboxing before it is enabled.")
