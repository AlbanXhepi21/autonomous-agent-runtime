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
from app.tools.base import Tool, ToolInputError
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
            arguments=safe_log_value(
                _safe_logged_arguments(tool_name, arguments)
            ),
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

        filesystem = getattr(tool, "operation_kind", None) == "filesystem"
        command = getattr(tool, "operation_kind", None) == "command"
        python_execution = getattr(tool, "operation_kind", None) == "python"
        repository = getattr(tool, "operation_kind", None) == "repository"
        if filesystem:
            log_event(
                self._logger,
                logging.INFO,
                "filesystem_operation_started",
                **event_fields,
                relative_path=safe_log_value(arguments.get("path", "")),
            )
        if command:
            log_event(
                self._logger,
                logging.INFO,
                "command_execution_started",
                **event_fields,
                command=safe_log_value(arguments.get("command", "")),
                args_summary=_command_args_summary(arguments.get("args")),
            )
        if python_execution:
            log_event(
                self._logger,
                logging.INFO,
                "python_execution_started",
                **event_fields,
                code_bytes=_code_bytes(arguments.get("code")),
            )
        if repository:
            event = "repository_search_started" if tool.name == "search_files" else "repository_inspection"
            log_event(self._logger, logging.INFO, event, **event_fields, repository_tool=tool.name)
        execution_fields = {
            **event_fields,
            "filesystem": filesystem,
            "relative_path": arguments.get("path", ""),
            "command_operation": command,
            "command": arguments.get("command", ""),
            "args_summary": _command_args_summary(arguments.get("args")),
            "python_execution": python_execution,
            "code_bytes": _code_bytes(arguments.get("code")),
            "repository": repository,
        }

        argument_error = self._validate_arguments(tool, arguments)
        if argument_error:
            return self._finish(
                self._failure(argument_error, tool_name=tool.name), started_at, execution_fields
            )

        try:
            if getattr(tool, "requires_run_id", False):
                output = await tool.execute_for_run(run_id=run_id, **dict(arguments))
            else:
                output = await tool.execute(**dict(arguments))
        except ToolInputError as error:
            return self._finish(
                self._failure(str(error), tool_name=tool.name),
                started_at,
                execution_fields,
            )
        except (TypeError, ValueError, ZeroDivisionError):
            return self._finish(
                self._failure("Tool rejected the supplied arguments.", tool_name=tool.name),
                started_at,
                execution_fields,
            )
        except Exception:
            return self._finish(
                self._failure("Tool execution failed.", tool_name=tool.name),
                started_at,
                execution_fields,
            )

        return self._finish(
            ToolResult(
                success=True,
                output=safe_observation_value(
                    output, max_length=getattr(tool, "max_observation_length", 200)
                ),
                metadata={"tool_name": tool.name},
            ),
            started_at,
            execution_fields,
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
        if event_fields.get("filesystem"):
            event = "filesystem_operation_finished" if result.success else "filesystem_operation_denied"
            log_event(
                self._logger,
                logging.INFO if result.success else logging.WARNING,
                event,
                run_id=event_fields.get("run_id"),
                iteration=event_fields.get("iteration"),
                tool=event_fields.get("tool"),
                relative_path=safe_log_value(event_fields.get("relative_path", "")),
                success=result.success,
                duration_ms=fields["duration_ms"],
            )
        if event_fields.get("command_operation"):
            output = result.output if isinstance(result.output, Mapping) else {}
            if not result.success:
                event, level = "command_execution_denied", logging.WARNING
            elif output.get("denied"):
                event, level = "command_execution_denied", logging.WARNING
            elif output.get("timed_out"):
                event, level = "command_execution_timeout", logging.WARNING
            elif output.get("success") is False:
                event, level = "command_execution_failed", logging.WARNING
            else:
                event, level = "command_execution_finished", logging.INFO
            log_event(
                self._logger,
                level,
                event,
                run_id=event_fields.get("run_id"),
                iteration=event_fields.get("iteration"),
                command=safe_log_value(event_fields.get("command", "")),
                args_summary=event_fields.get("args_summary"),
                duration_ms=output.get("duration_ms", fields["duration_ms"]),
                return_code=output.get("return_code"),
            )
        if event_fields.get("python_execution"):
            output = result.output if isinstance(result.output, Mapping) else {}
            if output.get("timed_out"):
                event, level = "python_execution_timeout", logging.WARNING
            elif not result.success or output.get("success") is False:
                event, level = "python_execution_failed", logging.WARNING
            else:
                event, level = "python_execution_finished", logging.INFO
            log_event(
                self._logger,
                level,
                event,
                run_id=event_fields.get("run_id"),
                iteration=event_fields.get("iteration"),
                code_bytes=event_fields.get("code_bytes"),
                duration_ms=output.get("duration_ms", fields["duration_ms"]),
                return_code=output.get("return_code"),
            )
        if event_fields.get("repository"):
            event = "repository_search_finished" if event_fields.get("tool") == "search_files" else "repository_inspection"
            log_event(
                self._logger, logging.INFO if result.success else logging.WARNING, event,
                run_id=event_fields.get("run_id"), iteration=event_fields.get("iteration"),
                repository_tool=event_fields.get("tool"), success=result.success,
            )
        if event_fields.get("tool") == "write_file" and result.success:
            log_event(
                self._logger, logging.INFO, "repository_file_modified",
                run_id=event_fields.get("run_id"), iteration=event_fields.get("iteration"),
                relative_path=safe_log_value(event_fields.get("relative_path", "")),
            )
        if event_fields.get("tool") == "register_artifact":
            output = result.output if isinstance(result.output, Mapping) else {}
            artifact = output.get("artifact") if isinstance(output, Mapping) else None
            if result.success and isinstance(artifact, Mapping):
                fields = {"run_id": event_fields.get("run_id"), "artifact_id": artifact.get("id"), "name": artifact.get("name"), "artifact_type": artifact.get("artifact_type"), "size": artifact.get("size")}
                log_event(self._logger, logging.INFO, "artifact_created", **fields)
                log_event(self._logger, logging.INFO, "artifact_registered", **fields)
            else:
                log_event(self._logger, logging.WARNING, "artifact_registration_failed", run_id=event_fields.get("run_id"), error=safe_error_message(result.error or "Artifact registration failed."))
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


def _safe_logged_arguments(
    tool_name: str, arguments: Mapping[str, Any] | None
) -> Mapping[str, Any] | None:
    """Avoid retaining filesystem file content in DEBUG execution logs."""

    if not isinstance(arguments, Mapping):
        return arguments
    if tool_name == "run_command":
        return {
            key: (f"[{len(value)} arguments]" if key == "args" and isinstance(value, list) else value)
            for key, value in arguments.items()
        }
    if tool_name == "python_exec":
        return {
            key: (f"[{len(value.encode('utf-8'))} bytes of code]" if key == "code" and isinstance(value, str) else value)
            for key, value in arguments.items()
        }
    if tool_name != "write_file":
        return arguments
    return {
        key: "[OMITTED FILE CONTENT]" if key == "content" else value
        for key, value in arguments.items()
    }


def _command_args_summary(args: Any) -> str:
    """Record only argv cardinality; command arguments may contain sensitive values."""

    return f"{len(args)} arguments" if isinstance(args, list) else "0 arguments"


def _code_bytes(code: Any) -> int:
    """Report source size without retaining source text in execution events."""

    return len(code.encode("utf-8")) if isinstance(code, str) else 0
