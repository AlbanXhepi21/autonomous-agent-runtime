"""Structured execution boundary for runtime tools."""

from collections.abc import Mapping
import logging
from time import perf_counter
from typing import Any

from app.core.exceptions import UnknownToolError
from app.core.logging import (
    log_event,
    safe_error_message,
    safe_log_value,
    safe_observation_value,
)
from app.tools.base import Tool
from app.tools.models import ToolResult
from app.tools.registry import ToolRegistry


class ToolExecutor:
    """Validate and execute registered tools without exposing exceptions to the agent."""

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self._tool_registry = tool_registry
        self._logger = logging.getLogger(__name__)

    async def execute(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        run_id: str | None = None,
        iteration: int | None = None,
    ) -> ToolResult:
        """Run one tool request and return its safe, structured outcome."""

        started_at = perf_counter()
        event_fields = {
            "run_id": run_id,
            "iteration": iteration,
            "tool": tool_name if isinstance(tool_name, str) else "",
        }
        log_event(self._logger, logging.INFO, "tool_execution_started", **event_fields)
        log_event(
            self._logger,
            logging.DEBUG,
            "tool_execution_arguments",
            **event_fields,
            arguments=safe_log_value(arguments or {}),
        )

        if not isinstance(tool_name, str) or not tool_name.strip():
            return self._finish(
                self._failure("Unknown tool.", tool_name=""), started_at, event_fields
            )

        if arguments is None:
            arguments = {}
        if not isinstance(arguments, Mapping):
            return self._finish(
                self._failure("Invalid tool arguments.", tool_name=tool_name),
                started_at,
                event_fields,
            )

        try:
            tool = self._tool_registry.get(tool_name)
        except UnknownToolError:
            return self._finish(
                self._failure(f"Unknown tool: {tool_name}.", tool_name=tool_name),
                started_at,
                event_fields,
            )

        argument_error = self._validate_arguments(tool, arguments)
        if argument_error:
            return self._finish(
                self._failure(argument_error, tool_name=tool.name), started_at, event_fields
            )

        try:
            output = await tool.execute(**dict(arguments))
        except (TypeError, ValueError, ZeroDivisionError):
            return self._finish(
                self._failure("Tool rejected the supplied arguments.", tool_name=tool.name),
                started_at,
                event_fields,
            )
        except Exception:
            return self._finish(
                self._failure("Tool execution failed.", tool_name=tool.name),
                started_at,
                event_fields,
            )

        return self._finish(
            ToolResult(
                success=True,
                output=safe_observation_value(output),
                metadata={"tool_name": tool.name},
            ),
            started_at,
            event_fields,
        )

    def _finish(
        self,
        result: ToolResult,
        started_at: float,
        event_fields: dict[str, Any],
    ) -> ToolResult:
        """Log a safe terminal execution event and return the tool result."""

        fields = {
            **event_fields,
            "success": result.success,
            "duration_ms": round((perf_counter() - started_at) * 1000),
        }
        if result.success:
            log_event(self._logger, logging.INFO, "tool_execution_finished", **fields)
        else:
            log_event(
                self._logger,
                logging.WARNING,
                "tool_execution_failed",
                **fields,
                error=safe_error_message(result.error or "Tool execution failed."),
            )
        return result

    @staticmethod
    def _validate_arguments(tool: Tool, arguments: Mapping[str, Any]) -> str | None:
        """Perform the small JSON-schema subset used by the local tool contract."""

        schema = tool.arguments_schema
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        for name in required:
            if name not in arguments:
                return f"Invalid tool arguments: missing required argument '{name}'."

        if schema.get("additionalProperties") is False:
            unexpected = set(arguments) - set(properties)
            if unexpected:
                name = sorted(unexpected)[0]
                return f"Invalid tool arguments: unexpected argument '{name}'."

        for name, value in arguments.items():
            definition = properties.get(name)
            if not isinstance(definition, Mapping):
                continue
            expected_type = definition.get("type")
            if expected_type and not ToolExecutor._matches_json_type(value, expected_type):
                return f"Invalid tool arguments: '{name}' must be a {expected_type}."

        return None

    @staticmethod
    def _matches_json_type(value: Any, expected_type: str) -> bool:
        """Check the primitive JSON-schema types needed by registered tools."""

        type_checks = {
            "string": lambda value: isinstance(value, str),
            "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
            "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
            "boolean": lambda value: isinstance(value, bool),
            "array": lambda value: isinstance(value, list),
            "object": lambda value: isinstance(value, Mapping),
        }
        check = type_checks.get(expected_type)
        return check(value) if check else True

    @staticmethod
    def _failure(error: str, *, tool_name: str) -> ToolResult:
        """Create a failure result that can safely become an LLM observation."""

        return ToolResult(
            success=False,
            error=safe_error_message(error),
            metadata={"tool_name": tool_name},
        )
