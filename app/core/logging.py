"""Small, safe structured logging helpers for development runtime events."""

import json
import logging
import math
import re
from collections.abc import Mapping
from typing import Any

_SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "password",
    "secret",
    "token",
    "cookie",
)
_MAX_LOG_VALUE_LENGTH = 200


class StructuredEventFormatter(logging.Formatter):
    """Append explicitly supplied event fields as compact JSON."""

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        fields = getattr(record, "event_fields", None)
        if not fields:
            return formatted
        return f"{formatted} {json.dumps(fields, default=str, sort_keys=True)}"


class PrettyEventFormatter(logging.Formatter):
    """Render concise development-friendly agent events."""

    def format(self, record: logging.LogRecord) -> str:
        fields = {
            key: value
            for key, value in getattr(record, "event_fields", {}).items()
            if value is not None
        }
        event = record.getMessage()
        run_id = fields.pop("run_id", None)
        prefix = f" run={str(run_id)[:8]}" if run_id else ""
        return f"{self.formatTime(record, self.datefmt)} {record.levelname:<5}{prefix} {_pretty_event(event, fields)}"


def configure_logging(log_level: str = "INFO", log_format: str = "pretty") -> None:
    """Configure the application logger without adding external dependencies."""

    logger = logging.getLogger("app")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    formatter: logging.Formatter
    if log_format.lower() == "json":
        formatter = StructuredEventFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    else:
        formatter = PrettyEventFormatter(datefmt="%H:%M:%S")

    handler = next(
        (
            handler
            for handler in logger.handlers
            if getattr(handler, "_agent_structured_logging", False)
        ),
        None,
    )
    if handler is None:
        handler = logging.StreamHandler()
        handler._agent_structured_logging = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    handler.setFormatter(formatter)
    logger.propagate = False


def log_event(
    logger: logging.Logger, level: int, event: str, **fields: Any
) -> None:
    """Emit an event with fields kept separate from the formatted message."""

    logger.log(level, event, extra={"event_fields": fields})


def safe_log_value(value: Any, *, max_length: int = _MAX_LOG_VALUE_LENGTH) -> Any:
    """Recursively redact sensitive mappings and truncate large string values."""

    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]"
            if _is_sensitive_key(str(key))
            else safe_log_value(item, max_length=max_length)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [safe_log_value(item, max_length=max_length) for item in value]
    if isinstance(value, str):
        return _truncate(value, max_length)
    return value


def safe_observation_value(value: Any, *, max_length: int = _MAX_LOG_VALUE_LENGTH) -> Any:
    """Return JSON-compatible tool output safe to retain in agent observations."""

    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]"
            if _is_sensitive_key(str(key))
            else safe_observation_value(item, max_length=max_length)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [safe_observation_value(item, max_length=max_length) for item in value]
    if isinstance(value, str):
        return _truncate(value, max_length)
    if isinstance(value, float) and not math.isfinite(value):
        return "[non-finite number]"
    if value is None or isinstance(value, bool | int | float):
        return value
    return "[unsupported tool output]"


def safe_error_message(error: BaseException | str) -> str:
    """Return a short error description suitable for application logs."""

    message = str(error)
    for key in _SENSITIVE_KEY_PARTS:
        message = re.sub(
            rf"(?i)({re.escape(key)}\s*[=:]\s*)[^\s,;]+",
            r"\1[REDACTED]",
            message,
        )
    return _truncate(message, _MAX_LOG_VALUE_LENGTH)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[:max_length - 3]}..."


def _pretty_event(event: str, fields: dict[str, Any]) -> str:
    """Translate known runtime events into compact, readable log messages."""

    if event == "agent_run_started":
        limits = (
            f"i{fields.pop('max_iterations', '?')}/t{fields.pop('max_tool_calls', '?')}"
            f"/e{fields.pop('max_recoverable_errors', '?')}/d"
            f"{fields.pop('max_consecutive_duplicate_actions', '?')}"
        )
        return f"started goal={_display_value(fields.pop('goal', ''))} limits={limits}"
    if event == "iteration_started":
        return (
            f"iter={fields.pop('iteration', '?')} started tools={fields.pop('tool_calls', '?')} "
            f"errors={fields.pop('errors', '?')}"
        )
    if event == "llm_action_selected":
        parts = [
            f"iter={fields.pop('iteration', '?')}",
            f"action={fields.pop('action', '?')}",
        ]
        if tool := fields.pop("tool", None):
            parts.append(f"tool={tool}")
        if skill := fields.pop("skill", None):
            parts.append(f"skill={skill}")
        if specialist := fields.pop("specialist", None):
            parts.append(f"specialist={specialist}")
        parts.append(f"llm={fields.pop('duration_ms', '?')}ms")
        return " ".join(parts)
    if event == "skill_loaded":
        return f"iter={fields.pop('iteration', '?')} skill_loaded={fields.pop('skill', '?')}"
    if event == "delegation_requested":
        return (
            f"iter={fields.pop('iteration', '?')} delegation={fields.pop('target_agent', '?')} "
            f"requested objective={_display_value(fields.pop('objective', ''))}"
        )
    if event == "delegation_invalid":
        return (
            f"iter={fields.pop('iteration', '?')} delegation={fields.pop('target_agent', '?')} "
            f"invalid error={_display_value(fields.pop('error', ''))}"
        )
    if event == "subagent_execution_started":
        return (
            f"subagent={fields.pop('agent', '?')} child={str(fields.pop('child_run_id', '?'))[:8]} "
            f"started"
        )
    if event in {"subagent_execution_finished", "subagent_execution_failed"}:
        return (
            f"subagent={fields.pop('agent', '?')} child={str(fields.pop('child_run_id', '?'))[:8]} "
            f"{'finished' if event.endswith('finished') else 'failed'} "
            f"iterations={fields.pop('iterations', '?')} tools={fields.pop('tool_calls', '?')} "
            f"duration={fields.pop('duration_ms', '?')}ms"
        )
    if event == "parallel_delegation_started":
        return (
            f"parallel_delegation count={fields.pop('delegation_count', '?')}/"
            f"{fields.pop('configured_limit', '?')} started"
        )
    if event in {"parallel_delegation_finished", "parallel_delegation_partial_failure"}:
        return (
            f"parallel_delegation {'finished' if event.endswith('finished') else 'partial_failure'} "
            f"success={fields.pop('successful_count', '?')} failed={fields.pop('failed_count', '?')} "
            f"duration={fields.pop('duration_ms', '?')}ms"
        )
    if event == "tool_execution_started":
        return f"iter={fields.pop('iteration', '?')} tool={fields.pop('tool', '?')} started"
    if event == "tool_execution_finished":
        return (
            f"iter={fields.pop('iteration', '?')} tool={fields.pop('tool', '?')} success "
            f"duration={fields.pop('duration_ms', '?')}ms"
        )
    if event == "tool_execution_failed":
        return (
            f"iter={fields.pop('iteration', '?')} tool={fields.pop('tool', '?')} failed "
            f"error={_display_value(fields.pop('error', ''))}"
        )
    if event.startswith("command_execution_"):
        return (
            f"command={fields.pop('command', '?')} {event.removeprefix('command_execution_')} "
            f"args={fields.pop('args_summary', '?')} duration={fields.pop('duration_ms', '?')}ms "
            f"return_code={fields.pop('return_code', '?')}"
        )
    if event.startswith("python_execution_"):
        return (
            f"python {event.removeprefix('python_execution_')} "
            f"code={fields.pop('code_bytes', '?')}B duration={fields.pop('duration_ms', '?')}ms "
            f"return_code={fields.pop('return_code', '?')}"
        )
    if event == "repository_search_started":
        return f"repository search started tool={fields.pop('repository_tool', '?')}"
    if event == "repository_search_finished":
        return f"repository search finished tool={fields.pop('repository_tool', '?')} success={fields.pop('success', '?')}"
    if event == "repository_file_modified":
        return f"repository file modified path={_display_value(fields.pop('relative_path', ''))}"
    if event == "repository_inspection":
        return f"repository inspection tool={fields.pop('repository_tool', '?')}"
    if event in {"artifact_created", "artifact_registered"}:
        return f"artifact {event.removeprefix('artifact_')} id={fields.pop('artifact_id', '?')} name={_display_value(fields.pop('name', ''))}"
    if event == "artifact_registration_failed":
        return "artifact registration failed"
    if event == "duplicate_action_detected":
        return (
            f"iter={fields.pop('iteration', '?')} duplicate_action tool={fields.pop('tool', '?')} "
            f"count={fields.pop('duplicate_count', '?')}"
        )
    if event == "duplicate_delegation_detected":
        return (
            f"iter={fields.pop('iteration', '?')} duplicate_delegation "
            f"agent={fields.pop('target_agent', '?')} count={fields.pop('duplicate_count', '?')}"
        )
    if event == "delegation_limit_reached":
        return (
            f"delegation_limit type={fields.pop('limit_type', '?')} "
            f"value={fields.pop('current_value', '?')}/{fields.pop('configured_limit', '?')}"
        )
    if event == "runtime_limit_reached":
        return (
            f"limit_reached type={fields.pop('limit_type', '?')} "
            f"value={fields.pop('current_value', '?')}/{fields.pop('configured_limit', '?')}"
        )
    if event == "agent_finished":
        return (
            f"finished status={fields.pop('stop_reason', '?')} iterations={fields.pop('iterations', '?')} "
            f"tools={fields.pop('tool_calls', '?')} errors={fields.pop('errors', '?')} "
            f"duration={fields.pop('duration_ms', '?')}ms"
        )
    return " ".join([event, *(_format_fields(fields))])


def _format_fields(fields: dict[str, Any]) -> list[str]:
    return [f"{key}={_display_value(value)}" for key, value in fields.items()]


def _display_value(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value)
    return json.dumps(value, default=str, separators=(",", ":"))
