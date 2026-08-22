"""Structured execution boundary for runtime tools.

One path, four phases: resolve and validate the request, authorize it, run the
tool, then report the outcome. What a particular family of tools should log or
trace lives in observers.py, so adding a tool family does not mean editing this
file.
"""

import logging
from collections.abc import Mapping
from time import perf_counter
from typing import Any

from app.core.exceptions import UnknownToolError
from app.core.logging import (
    log_event,
    safe_error_message,
    safe_log_value,
    safe_observation_value,
)
from app.observability import TraceEventType, TraceRecorder
from app.security import (
    ContentTrust,
    PolicyDecision,
    PolicyResult,
    SecurityAction,
    SecurityPolicy,
    SecuritySubject,
    capability_for_tool,
    external_content_for_tool,
    injection_indicators,
    resource_for_tool,
)
from app.tools.base import Tool, ToolExecutionError, ToolInputError
from app.tools.contracts import ToolResult
from app.tools.execution.observers import ToolObserver, observers_for
from app.tools.execution.redaction import safe_logged_arguments, safe_sql_for_trace
from app.tools.registry import ToolRegistry


class ToolExecutor:
    """Validate and execute registered tools without exposing exceptions to the agent."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        *,
        security_policy: SecurityPolicy | None = None,
        trace_recorder: TraceRecorder | None = None,
        expose_sql: bool = False,
        max_sql_chars: int = 4_000,
    ) -> None:
        self._tool_registry = tool_registry
        self._security_policy = security_policy or SecurityPolicy.primary()
        self._approved_execution_token = object()
        self._trace_recorder = trace_recorder
        self._expose_sql = expose_sql
        self._max_sql_chars = max_sql_chars
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
        action = self._security_action(tool, arguments)
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
        fields: dict[str, Any] = {
            "run_id": run_id,
            "iteration": iteration,
            "tool": tool_name if isinstance(tool_name, str) else "",
        }
        self._record_request(fields, tool_name, arguments, run_id, iteration)

        resolved = self._resolve(tool_name, arguments)
        if isinstance(resolved, ToolResult):
            return self._finish(resolved, started_at, fields, ())
        tool, arguments = resolved

        observers = observers_for(tool)
        for observer in observers:
            fields.update(observer.context(tool, arguments))
            if observer.run_context is not None and self._trace_recorder is not None and run_id:
                fields.update(observer.run_context(self._trace_recorder, run_id))
        if self._expose_sql:
            fields["sql_for_trace"] = safe_sql_for_trace(arguments.get("sql"), self._max_sql_chars)
        for observer in observers:
            if observer.on_started is not None:
                observer.on_started(self._logger, fields, arguments)

        if argument_error := self._validate_arguments(tool, arguments):
            return self._finish(
                self._failure(argument_error, tool_name=tool.name, failure_category="tool_validation_error"),
                started_at, fields, observers,
            )

        subject = subject or SecuritySubject(
            agent_name="runtime", agent_type="system", run_id=run_id or "unscoped"
        )
        fields["agent"] = subject.agent_name
        if self._trace_recorder is not None and run_id:
            for observer in observers:
                if observer.on_trace_start is not None:
                    observer.on_trace_start(self._trace_recorder, run_id, iteration, fields, arguments)

        denial = self._authorize(tool, arguments, subject, run_id, iteration, approval_granted)
        if denial is not None:
            return self._finish(denial, started_at, fields, observers)

        outcome = await self._run(tool, arguments, run_id, fields)
        return self._finish(outcome, started_at, fields, observers)

    def _record_request(
        self, fields: dict[str, Any], tool_name: Any, arguments: Mapping[str, Any] | None,
        run_id: str | None, iteration: int | None,
    ) -> None:
        """Log and trace that a request arrived, before it is known to be valid."""

        log_event(self._logger, logging.INFO, "tool_execution_started", **fields)
        if self._trace_recorder is not None and run_id:
            self._trace_recorder.record(
                run_id, TraceEventType.TOOL_STARTED, iteration=iteration,
                metadata={"tool_name": fields["tool"], "arguments": safe_logged_arguments(tool_name, arguments)},
            )
        log_event(
            self._logger, logging.DEBUG, "tool_execution_arguments", **fields,
            arguments=safe_log_value(safe_logged_arguments(tool_name, arguments)),
        )

    def _resolve(
        self, tool_name: Any, arguments: Mapping[str, Any] | None
    ) -> tuple[Tool, Mapping[str, Any]] | ToolResult:
        """Return the tool and its arguments, or the failure that stops the request."""

        if not isinstance(tool_name, str) or not tool_name.strip():
            return self._failure("Unknown tool.", tool_name="", failure_category="unknown_failure")
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, Mapping):
            return self._failure(
                "Invalid tool arguments.", tool_name=tool_name, failure_category="tool_validation_error"
            )
        try:
            return self._tool_registry.get(tool_name), arguments
        except UnknownToolError:
            return self._failure(
                f"Unknown tool: {tool_name}.", tool_name=tool_name, failure_category="unknown_failure"
            )

    @staticmethod
    def _security_action(tool: Tool, arguments: Mapping[str, Any]) -> SecurityAction:
        return SecurityAction(
            capability=capability_for_tool(tool.name), tool_name=tool.name,
            resource=resource_for_tool(tool.name, arguments),
        )

    def _authorize(
        self, tool: Tool, arguments: Mapping[str, Any], subject: SecuritySubject,
        run_id: str | None, iteration: int | None, approval_granted: bool,
    ) -> ToolResult | None:
        """Return a failure when policy does not permit the action, otherwise None."""

        action = self._security_action(tool, arguments)
        try:
            policy_result = self._security_policy.evaluate(subject, action)
        except Exception:
            infrastructure_failed = True
            policy_result = PolicyResult(
                decision=PolicyDecision.DENY, reason="Security policy evaluation failed.",
                policy_id="security.policy_evaluation_failed", capability=action.capability,
            )
        else:
            infrastructure_failed = False

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
            self._trace_recorder.record(
                run_id, TraceEventType.SECURITY_POLICY_EVALUATED, iteration=iteration,
                success=policy_result.decision == PolicyDecision.ALLOW,
                metadata={
                    "capability": security_fields["capability"], "decision": security_fields["decision"],
                    "policy_id": policy_result.policy_id,
                    "risk_level": policy_result.metadata.get("risk_level"),
                },
            )
            if infrastructure_failed:
                self._trace_recorder.record(
                    run_id, TraceEventType.OPERATION_FAILED, iteration=iteration,
                    metadata={"failure_category": "policy_failure", "source": "security_policy", "attempt": 1},
                )

        permitted = policy_result.decision == PolicyDecision.ALLOW or (
            approval_granted and policy_result.decision == PolicyDecision.REQUIRE_APPROVAL
        )
        if not permitted:
            event = (
                "security_approval_required"
                if policy_result.decision == PolicyDecision.REQUIRE_APPROVAL
                else "security_action_denied"
            )
            log_event(self._logger, logging.WARNING, event, **security_fields)
            return self._policy_failure(tool.name, policy_result)
        log_event(self._logger, logging.INFO, "security_action_allowed", **security_fields)
        return None

    async def _run(
        self, tool: Tool, arguments: Mapping[str, Any], run_id: str | None, fields: dict[str, Any]
    ) -> ToolResult:
        """Execute the tool, converting any failure into a safe structured result."""

        try:
            if getattr(tool, "requires_run_id", False):
                runtime_arguments = dict(arguments)
                if "query_id" in fields:
                    runtime_arguments["query_id"] = fields["query_id"]
                output = await tool.execute_for_run(run_id=run_id, **runtime_arguments)
            else:
                output = await tool.execute(**dict(arguments))
            if "query_id" in fields and isinstance(output, Mapping):
                output = {**output, "query_id": fields["query_id"]}
        except ToolInputError as error:
            return self._failure(str(error), tool_name=tool.name, failure_category="tool_validation_error")
        except ToolExecutionError as error:
            return self._failure(str(error), tool_name=tool.name, failure_category=error.failure_category)
        except (TypeError, ValueError, ZeroDivisionError):
            return self._failure(
                "Tool rejected the supplied arguments.", tool_name=tool.name,
                failure_category="tool_validation_error",
            )
        except Exception:
            return self._failure("Tool execution failed.", tool_name=tool.name)

        untrusted = external_content_for_tool(tool.name, arguments, output)
        if untrusted is not None:
            log_event(
                self._logger, logging.INFO, "untrusted_content_ingested", run_id=run_id,
                source_type=untrusted.source_type, source_identifier=safe_log_value(untrusted.source),
            )
            for indicator in injection_indicators(untrusted.content):
                log_event(
                    self._logger, logging.WARNING, "prompt_injection_indicator_detected", run_id=run_id,
                    source_type=untrusted.source_type,
                    source_identifier=safe_log_value(untrusted.source), matched_heuristic=indicator,
                )
        return ToolResult(
            success=True,
            output=safe_observation_value(output, max_length=getattr(tool, "max_observation_length", 200)),
            metadata={"tool_name": tool.name},
            trust=untrusted.trust if untrusted else ContentTrust.TOOL_OUTPUT,
            source_type=untrusted.source_type if untrusted else None,
            source_identifier=untrusted.source if untrusted else None,
        )

    def _finish(
        self,
        result: ToolResult,
        started_at: float,
        fields: dict[str, Any],
        observers: tuple[ToolObserver, ...],
    ) -> ToolResult:
        """Log a safe terminal execution event and return the tool result."""

        duration_ms = round((perf_counter() - started_at) * 1000)
        terminal = {**fields, "success": result.success, "duration_ms": duration_ms}
        if result.success:
            log_event(self._logger, logging.INFO, "tool_execution_finished", **terminal)
        else:
            log_event(
                self._logger, logging.WARNING, "tool_execution_failed", **terminal,
                error=safe_error_message(result.error or "Tool execution failed."),
            )
        for observer in observers:
            if observer.on_finished is not None:
                observer.on_finished(self._logger, fields, result, duration_ms)

        run_id = fields.get("run_id")
        if self._trace_recorder is None or not isinstance(run_id, str) or not run_id:
            return result
        self._trace_recorder.record(
            run_id, TraceEventType.TOOL_FINISHED if result.success else TraceEventType.TOOL_FAILED,
            iteration=fields.get("iteration"), duration_ms=duration_ms, success=result.success,
            metadata={
                "tool_name": fields.get("tool"), "result_metadata": result.metadata,
                "error": result.error if not result.success else None,
            },
        )
        if not result.success:
            self._trace_recorder.record(
                run_id, TraceEventType.OPERATION_FAILED, iteration=fields.get("iteration"),
                metadata={
                    "failure_category": result.metadata.get("failure_category", "tool_failure"),
                    "source": "tool", "attempt": 1,
                },
            )
        for observer in observers:
            if observer.on_trace_finish is not None:
                observer.on_trace_finish(self._trace_recorder, run_id, fields, result, duration_ms)
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
