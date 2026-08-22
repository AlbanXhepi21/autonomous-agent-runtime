"""Thin public tool adapter for restricted local Python execution."""

from typing import Any

from app.environment.python import PythonExecutor
from app.tools.base import Tool


class PythonExecTool(Tool):
    """Keep the existing python_exec tool name while delegating execution policy."""

    operation_kind = "python"

    def __init__(self, python_executor: PythonExecutor) -> None:
        self._python_executor = python_executor
        self.max_observation_length = python_executor.max_output_bytes

    @property
    def name(self) -> str:
        return "python_exec"

    @property
    def description(self) -> str:
        return "Run short Python code in a restricted local child process for calculations and data work."

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
            "additionalProperties": False,
        }

    async def execute(self, **arguments: Any) -> dict[str, object]:
        return (await self._python_executor.execute(arguments["code"])).model_dump()
