"""Thin tool adapter for controlled workspace command execution."""

from typing import Any

from app.environment.commands import CommandExecutor
from app.tools.base import Tool


class RunCommandTool(Tool):
    """Expose the CommandExecutor without embedding subprocess policy in the tool."""

    operation_kind = "command"

    def __init__(self, command_executor: CommandExecutor) -> None:
        self._command_executor = command_executor
        self.max_observation_length = command_executor.max_output_bytes

    @property
    def name(self) -> str:
        return "run_command"

    @property
    def description(self) -> str:
        return "Run one allowlisted development command in the current workspace using structured arguments."

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Allowlisted executable name."},
                "args": {"type": "array", "items": {"type": "string"}, "description": "Structured argv arguments."},
                "working_directory": {"type": "string", "description": "Optional relative workspace directory."},
            },
            "required": ["command"],
            "additionalProperties": False,
        }

    async def execute(self, **arguments: Any) -> dict[str, object]:
        result = await self._command_executor.execute(
            arguments["command"], arguments.get("args", []),
            working_directory=arguments.get("working_directory"),
        )
        return result.model_dump()
