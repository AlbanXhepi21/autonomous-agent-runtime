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
from app.security import (
    PolicyDecision,
    PolicyResult,
    ContentTrust,
    SecurityAction,
    SecurityPolicy,
    SecuritySubject,
    capability_for_tool,
    external_content_for_tool,
    injection_indicators,
    resource_for_tool,
)
from app.tools.base import Tool, ToolExecutionError, ToolInputError
from app.tools.models import ToolResult
from app.tools.registry import ToolRegistry
from app.observability import TraceEventType, TraceRecorder


class ToolExecutor:
    """Validate and execute registered tools without exposing exceptions to the agent."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        *,
        security_policy: SecurityPolicy | None = None,
        trace_recorder: TraceRecorder | None = None,
    ) -> None:
        self._tool_registry = tool_registry
        self._security_policy = security_policy or SecurityPolicy.primary()
        self._approved_execution_token = object()
        self._trace_recorder = trace_recorder
        self._logger = logging.getLogger(__name__)

    def evaluate_policy(
        self, tool_name: str, arguments: Mapping[str, Any], subject: SecuritySubject
    ) -> tuple[PolicyResult, SecurityAction] | None:
        """Return the gate decision only for a valid registered tool action."""

        try:
            tool = self._tool_registry.get(tool_name)
        except UnknownToolError:
            return None
        if self._validate_arguments(tool, arguments):
            return None
        action = SecurityAction(
            capability=capability_for_tool(tool.name), tool_name=tool.name,
            resource=resource_for_tool(tool.name, arguments),
        )
        try:
            return self._security_policy.evaluate(subject, action), action
        except Exception:
            # Security infrastructure failures are never permission grants.
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason="Security policy evaluation failed.",
                policy_id="security.policy_evaluation_failed",
                capability=action.capability,
            ), action

    async def execute(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        run_id: str | None = None,
        iteration: int | None = None,
        subject: SecuritySubject | None = None,
    ) -> ToolResult:
        """Run one tool request and return its safe, structured outcome."""

        return await self._execute(
            tool_name, arguments, run_id=run_id, iteration=iteration, subject=subject,
            approval_granted=False,
        )

    async def execute_approved(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        run_id: str | None = None,
        iteration: int | None = None,
        subject: SecuritySubject | None = None,
        approval_token: object | None = None,
    ) -> ToolResult:
        """Internal resume path; only AgentRunner calls this after a claimed approval."""

        if approval_token is not self._approved_execution_token:
            return ToolResult(
                success=False,
                error="Approved execution was not validated by the runtime.",
                metadata={"tool_name": tool_name, "policy_id": "security.invalid_approval_execution"},
            )

        return await self._execute(
            tool_name, arguments, run_id=run_id, iteration=iteration, subject=subject,
            approval_granted=True,
        )

    async def _execute(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        run_id: str | None = None,
        iteration: int | None = None,
        subject: SecuritySubject | None = None,
        approval_granted: bool,
    ) -> ToolResult:
        """Shared implementation; the public execute path can never bypass approval."""

        started_at = perf_counter()
        event_fields = {
            "run_id": run_id,
            "iteration": iteration,
            "tool": tool_name if isinstance(tool_name, str) else "",
        }
        log_event(self._logger, logging.INFO, "tool_execution_started", **event_fields)
        if self._trace_recorder is not None and run_id:
            self._trace_recorder.record(run_id, TraceEventType.TOOL_STARTED, iteration=iteration,
                metadata={"tool_name": event_fields["tool"], "arguments": _safe_logged_arguments(tool_name, arguments)})
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
                self._failure("Unknown tool.", tool_name="", failure_category="unknown_failure"), started_at, event_fields
            )

        if arguments is None:
            arguments = {}
        if not isinstance(arguments, Mapping):
            return self._finish(
                self._failure("Invalid tool arguments.", tool_name=tool_name, failure_category="tool_validation_error"),
                started_at,
                event_fields,
            )

        try:
            tool = self._tool_registry.get(tool_name)
        except UnknownToolError:
            return self._finish(
                self._failure(f"Unknown tool: {tool_name}.", tool_name=tool_name, failure_category="unknown_failure"),
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
            "database_table_names": _database_table_names(tool.name, arguments),
        }

        argument_error = self._validate_arguments(tool, arguments)
        if argument_error:
            return self._finish(
                self._failure(argument_error, tool_name=tool.name, failure_category="tool_validation_error"), started_at, execution_fields
            )

        subject = subject or SecuritySubject(
            agent_name="runtime", agent_type="system", run_id=run_id or "unscoped"
        )
        execution_fields["agent"] = subject.agent_name
        security_action = SecurityAction(
            capability=capability_for_tool(tool.name), tool_name=tool.name,
            resource=resource_for_tool(tool.name, arguments),
        )
        try:
            policy_result = self._security_policy.evaluate(subject, security_action)
        except Exception:
            policy_infrastructure_failed = True
            policy_result = PolicyResult(
                decision=PolicyDecision.DENY, reason="Security policy evaluation failed.",
                policy_id="security.policy_evaluation_failed", capability=security_action.capability,
            )
        else:
            policy_infrastructure_failed = False
        security_fields = {
            "run_id": subject.run_id, "agent": subject.agent_name,
            "capability": policy_result.capability.value if policy_result.capability else "unknown",
            "decision": policy_result.decision.value, "policy_id": policy_result.policy_id,
        }
        log_event(
            self._logger, logging.INFO, "risk_assessment_created", **security_fields,
            risk_level=policy_result.metadata.get("risk_level"),
            risk_rule=policy_result.metadata.get("risk_rule"),
        )
        log_event(self._logger, logging.INFO, "security_policy_evaluated", **security_fields)
        if self._trace_recorder is not None and run_id:
            self._trace_recorder.record(run_id, TraceEventType.SECURITY_POLICY_EVALUATED, iteration=iteration,
                success=policy_result.decision == PolicyDecision.ALLOW,
                metadata={"capability": security_fields["capability"], "decision": security_fields["decision"],
                          "policy_id": policy_result.policy_id, "risk_level": policy_result.metadata.get("risk_level")})
            if policy_infrastructure_failed:
                self._trace_recorder.record(run_id, TraceEventType.OPERATION_FAILED, iteration=iteration,
                    metadata={"failure_category": "policy_failure", "source": "security_policy", "attempt": 1})
        if policy_result.decision != PolicyDecision.ALLOW and not (
            approval_granted and policy_result.decision == PolicyDecision.REQUIRE_APPROVAL
        ):
            event = (
                "security_approval_required"
                if policy_result.decision == PolicyDecision.REQUIRE_APPROVAL
                else "security_action_denied"
            )
            log_event(self._logger, logging.WARNING, event, **security_fields)
            return self._finish(
                self._policy_failure(tool.name, policy_result), started_at, execution_fields
            )
        log_event(self._logger, logging.INFO, "security_action_allowed", **security_fields)

        try:
            if getattr(tool, "requires_run_id", False):
                output = await tool.execute_for_run(run_id=run_id, **dict(arguments))
            else:
                output = await tool.execute(**dict(arguments))
        except ToolInputError as error:
            return self._finish(
                self._failure(str(error), tool_name=tool.name, failure_category="tool_validation_error"),
                started_at,
                execution_fields,
            )
        except ToolExecutionError as error:
            return self._finish(
                self._failure(str(error), tool_name=tool.name, failure_category=error.failure_category),
                started_at, execution_fields,
            )
        except (TypeError, ValueError, ZeroDivisionError):
            return self._finish(
                self._failure("Tool rejected the supplied arguments.", tool_name=tool.name, failure_category="tool_validation_error"),
                started_at,
                execution_fields,
            )
        except Exception:
            return self._finish(
                self._failure("Tool execution failed.", tool_name=tool.name),
                started_at,
                execution_fields,
            )

        untrusted_content = external_content_for_tool(tool.name, arguments, output)
        if untrusted_content is not None:
            log_event(self._logger, logging.INFO, "untrusted_content_ingested",
                      run_id=run_id, source_type=untrusted_content.source_type,
                      source_identifier=safe_log_value(untrusted_content.source))
            for indicator in injection_indicators(untrusted_content.content):
                log_event(self._logger, logging.WARNING, "prompt_injection_indicator_detected",
                          run_id=run_id, source_type=untrusted_content.source_type,
                          source_identifier=safe_log_value(untrusted_content.source), matched_heuristic=indicator)

        return self._finish(
            ToolResult(
                success=True,
                output=safe_observation_value(
                    output, max_length=getattr(tool, "max_observation_length", 200)
                ),
                metadata={"tool_name": tool.name},
                trust=untrusted_content.trust if untrusted_content else ContentTrust.TOOL_OUTPUT,
                source_type=untrusted_content.source_type if untrusted_content else None,
                source_identifier=untrusted_content.source if untrusted_content else None,
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
        duration_ms = fields["duration_ms"]
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
        run_id = event_fields.get("run_id")
        if self._trace_recorder is not None and isinstance(run_id, str) and run_id:
            self._trace_recorder.record(run_id,
                TraceEventType.TOOL_FINISHED if result.success else TraceEventType.TOOL_FAILED,
                iteration=event_fields.get("iteration"), duration_ms=duration_ms, success=result.success,
                metadata={"tool_name": event_fields.get("tool"), "result_metadata": result.metadata,
                          "error": result.error if not result.success else None})
            if not result.success:
                self._trace_recorder.record(run_id, TraceEventType.OPERATION_FAILED,
                    iteration=event_fields.get("iteration"), metadata={
                        "failure_category": result.metadata.get("failure_category", "tool_failure"),
                        "source": "tool", "attempt": 1,
                    })
            if event_fields.get("tool") == "register_artifact" and result.success:
                self._trace_recorder.record(run_id, TraceEventType.ARTIFACT_CREATED,
                    iteration=event_fields.get("iteration"), success=True,
                    metadata={"artifact": result.output})
            database_events = {
                "list_tables": TraceEventType.DATABASE_SCHEMA_LISTED,
                "describe_table": TraceEventType.DATABASE_TABLE_DESCRIBED,
                "get_table_relationships": TraceEventType.DATABASE_RELATIONSHIPS_INSPECTED,
                "search_schema": TraceEventType.DATABASE_SCHEMA_SEARCHED,
            }
            if (database_event := database_events.get(event_fields.get("tool"))) is not None:
                self._trace_recorder.record(run_id, database_event, iteration=event_fields.get("iteration"),
                    duration_ms=duration_ms, success=result.success, metadata={
                        "agent": event_fields.get("agent"), "operation": event_fields.get("tool"),
                        "table_names": event_fields.get("database_table_names", []),
                    })
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
    def _failure(error: str, *, tool_name: str, failure_category: str = "tool_failure") -> ToolResult:
        """Create a failure result that can safely become an LLM observation."""

        return ToolResult(
            success=False,
            error=safe_error_message(error),
            metadata={"tool_name": tool_name, "failure_category": failure_category},
        )

    @staticmethod
    def _policy_failure(tool_name: str, policy_result: PolicyResult) -> ToolResult:
        """Turn a non-executable policy result into a safe agent observation."""

        approval = policy_result.decision == PolicyDecision.REQUIRE_APPROVAL
        return ToolResult(
            success=False,
            error=(
                "This action requires human approval, which is not available in this runtime."
                if approval else "This action is not permitted by runtime security policy."
            ),
            metadata={
                "tool_name": tool_name,
                "security_decision": policy_result.decision.value,
                "capability": policy_result.capability.value if policy_result.capability else "unknown",
                "policy_id": policy_result.policy_id,
                "failure_category": "security_denial" if policy_result.policy_id != "security.policy_evaluation_failed" else "policy_failure",
            },
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


def _database_table_names(tool_name: object, arguments: object) -> list[str]:
    """Extract only safe table identifiers for database trace events."""

    if not isinstance(arguments, Mapping):
        return []
    names = arguments.get("table_names")
    if isinstance(names, list):
        return [item for item in names if isinstance(item, str)]
    if tool_name in {"describe_table", "get_table_relationships"} and isinstance(arguments.get("table_name"), str):
        return [arguments["table_name"]]
    return []
