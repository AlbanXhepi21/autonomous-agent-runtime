"""Per-family observation of tool execution.

The executor decides whether a tool may run and then runs it. What a particular
family of tools should log or trace is not its concern, so each family
registers an observer here instead of adding a branch to the executor.

An observer contributes four things, all optional:

  ``context``        fields derived from the arguments, carried to every phase
  ``on_started``     a log event before the tool runs
  ``on_trace_start`` a trace event before the tool runs
  ``on_finished``    a log event once the result is known
  ``on_trace_finish``trace events once the result is known
"""

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import log_event, safe_error_message, safe_log_value
from app.observability import TraceEventType, TraceRecorder
from app.tools.base import Tool
from app.tools.execution.redaction import (
    code_bytes,
    command_args_summary,
    database_table_names,
    query_quality_metadata,
)
from app.tools.models import ToolResult

Fields = dict[str, Any]


@dataclass(frozen=True)
class ToolObserver:
    """Logging and tracing for one family of tools."""

    name: str
    applies: Callable[[Tool], bool]
    context: Callable[[Tool, Mapping[str, Any]], Fields] = lambda tool, arguments: {}
    #: Fields that depend on what the run has already done, such as a sequence number.
    run_context: Callable[[TraceRecorder, str], Fields] | None = None
    on_started: Callable[[logging.Logger, Fields, Mapping[str, Any]], None] | None = None
    on_trace_start: Callable[[TraceRecorder, str, int | None, Fields, Mapping[str, Any]], None] | None = None
    on_finished: Callable[[logging.Logger, Fields, ToolResult, int], None] | None = None
    on_trace_finish: Callable[[TraceRecorder, str, Fields, ToolResult, int], None] | None = None


def _kind(operation_kind: str) -> Callable[[Tool], bool]:
    return lambda tool: getattr(tool, "operation_kind", None) == operation_kind


def _named(*names: str) -> Callable[[Tool], bool]:
    return lambda tool: tool.name in names


def _output(result: ToolResult) -> Mapping[str, Any]:
    return result.output if isinstance(result.output, Mapping) else {}


def _artifacts(output: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    items = output.get("artifacts")
    return [item for item in items if isinstance(item, Mapping)] if isinstance(items, list) else []


# --------------------------------------------------------------------------- filesystem


def _filesystem_started(logger: logging.Logger, fields: Fields, arguments: Mapping[str, Any]) -> None:
    log_event(
        logger, logging.INFO, "filesystem_operation_started",
        run_id=fields.get("run_id"), iteration=fields.get("iteration"), tool=fields.get("tool"),
        relative_path=safe_log_value(arguments.get("path", "")),
    )


def _filesystem_finished(
    logger: logging.Logger, fields: Fields, result: ToolResult, duration_ms: int
) -> None:
    event = "filesystem_operation_finished" if result.success else "filesystem_operation_denied"
    log_event(
        logger, logging.INFO if result.success else logging.WARNING, event,
        run_id=fields.get("run_id"), iteration=fields.get("iteration"), tool=fields.get("tool"),
        relative_path=safe_log_value(fields.get("relative_path", "")),
        success=result.success, duration_ms=duration_ms,
    )
    if fields.get("tool") == "write_file" and result.success:
        log_event(
            logger, logging.INFO, "repository_file_modified",
            run_id=fields.get("run_id"), iteration=fields.get("iteration"),
            relative_path=safe_log_value(fields.get("relative_path", "")),
        )


# --------------------------------------------------------------------------- command


def _command_started(logger: logging.Logger, fields: Fields, arguments: Mapping[str, Any]) -> None:
    log_event(
        logger, logging.INFO, "command_execution_started",
        run_id=fields.get("run_id"), iteration=fields.get("iteration"), tool=fields.get("tool"),
        command=safe_log_value(arguments.get("command", "")),
        args_summary=command_args_summary(arguments.get("args")),
    )


def _command_finished(
    logger: logging.Logger, fields: Fields, result: ToolResult, duration_ms: int
) -> None:
    output = _output(result)
    if not result.success or output.get("denied"):
        event, level = "command_execution_denied", logging.WARNING
    elif output.get("timed_out"):
        event, level = "command_execution_timeout", logging.WARNING
    elif output.get("success") is False:
        event, level = "command_execution_failed", logging.WARNING
    else:
        event, level = "command_execution_finished", logging.INFO
    log_event(
        logger, level, event,
        run_id=fields.get("run_id"), iteration=fields.get("iteration"),
        command=safe_log_value(fields.get("command", "")), args_summary=fields.get("args_summary"),
        duration_ms=output.get("duration_ms", duration_ms), return_code=output.get("return_code"),
    )


# --------------------------------------------------------------------------- python


def _python_started(logger: logging.Logger, fields: Fields, arguments: Mapping[str, Any]) -> None:
    log_event(
        logger, logging.INFO, "python_execution_started",
        run_id=fields.get("run_id"), iteration=fields.get("iteration"), tool=fields.get("tool"),
        code_bytes=code_bytes(arguments.get("code")),
    )


def _python_finished(
    logger: logging.Logger, fields: Fields, result: ToolResult, duration_ms: int
) -> None:
    output = _output(result)
    if output.get("timed_out"):
        event, level = "python_execution_timeout", logging.WARNING
    elif not result.success or output.get("success") is False:
        event, level = "python_execution_failed", logging.WARNING
    else:
        event, level = "python_execution_finished", logging.INFO
    log_event(
        logger, level, event,
        run_id=fields.get("run_id"), iteration=fields.get("iteration"),
        code_bytes=fields.get("code_bytes"),
        duration_ms=output.get("duration_ms", duration_ms), return_code=output.get("return_code"),
    )


# --------------------------------------------------------------------------- repository


def _repository_started(logger: logging.Logger, fields: Fields, arguments: Mapping[str, Any]) -> None:
    event = "repository_search_started" if fields.get("tool") == "search_files" else "repository_inspection"
    log_event(
        logger, logging.INFO, event, run_id=fields.get("run_id"),
        iteration=fields.get("iteration"), tool=fields.get("tool"), repository_tool=fields.get("tool"),
    )


def _repository_finished(
    logger: logging.Logger, fields: Fields, result: ToolResult, duration_ms: int
) -> None:
    event = "repository_search_finished" if fields.get("tool") == "search_files" else "repository_inspection"
    log_event(
        logger, logging.INFO if result.success else logging.WARNING, event,
        run_id=fields.get("run_id"), iteration=fields.get("iteration"),
        repository_tool=fields.get("tool"), success=result.success,
    )


# --------------------------------------------------------------------------- artifacts


def _artifact_finished(
    logger: logging.Logger, fields: Fields, result: ToolResult, duration_ms: int
) -> None:
    artifact = _output(result).get("artifact")
    if result.success and isinstance(artifact, Mapping):
        recorded = {
            "run_id": fields.get("run_id"), "artifact_id": artifact.get("id"),
            "name": artifact.get("name"), "artifact_type": artifact.get("artifact_type"),
            "size": artifact.get("size"),
        }
        log_event(logger, logging.INFO, "artifact_created", **recorded)
        log_event(logger, logging.INFO, "artifact_registered", **recorded)
    else:
        log_event(
            logger, logging.WARNING, "artifact_registration_failed", run_id=fields.get("run_id"),
            error=safe_error_message(result.error or "Artifact registration failed."),
        )


def _artifact_trace(
    recorder: TraceRecorder, run_id: str, fields: Fields, result: ToolResult, duration_ms: int
) -> None:
    if result.success:
        recorder.record(
            run_id, TraceEventType.ARTIFACT_CREATED, iteration=fields.get("iteration"),
            success=True, metadata={"artifact": result.output},
        )


# --------------------------------------------------------------------------- database schema

_SCHEMA_EVENTS = {
    "list_tables": TraceEventType.DATABASE_SCHEMA_LISTED,
    "describe_table": TraceEventType.DATABASE_TABLE_DESCRIBED,
    "get_table_relationships": TraceEventType.DATABASE_RELATIONSHIPS_INSPECTED,
    "search_schema": TraceEventType.DATABASE_SCHEMA_SEARCHED,
}


def _schema_trace(
    recorder: TraceRecorder, run_id: str, fields: Fields, result: ToolResult, duration_ms: int
) -> None:
    event = _SCHEMA_EVENTS.get(fields.get("tool"))
    if event is None:
        return
    recorder.record(
        run_id, event, iteration=fields.get("iteration"), duration_ms=duration_ms,
        success=result.success,
        metadata={
            "agent": fields.get("agent"), "operation": fields.get("tool"),
            "table_names": fields.get("database_table_names", []),
        },
    )


# --------------------------------------------------------------------------- sql


def _query_context(tool: Tool, arguments: Mapping[str, Any]) -> Fields:
    # A query is numbered even without a trace to number it against, so the tool
    # always receives an identifier to label its dataset with.
    return {
        "query_quality": query_quality_metadata(arguments.get("sql")),
        "query_id": "query_001",
    }


def _query_run_context(recorder: TraceRecorder, run_id: str) -> Fields:
    """Number queries within a run, so a trace can refer to "query 3"."""

    trace = recorder.get_trace(run_id)
    seen = sum(
        1 for event in (trace.events if trace else [])
        if event.event_type is TraceEventType.DATABASE_QUERY_VALIDATION_STARTED
    )
    return {"query_id": f"query_{seen + 1:03d}"}


def _query_trace_start(
    recorder: TraceRecorder, run_id: str, iteration: int | None, fields: Fields,
    arguments: Mapping[str, Any],
) -> None:
    recorder.record(
        run_id, TraceEventType.DATABASE_QUERY_VALIDATION_STARTED, iteration=iteration,
        metadata={
            "agent": fields.get("agent"), "operation": "query_database",
            "query_id": fields.get("query_id"),
        },
    )


def _query_trace_finish(
    recorder: TraceRecorder, run_id: str, fields: Fields, result: ToolResult, duration_ms: int
) -> None:
    output = _output(result)
    iteration = fields.get("iteration")
    metadata = {
        "agent": fields.get("agent"), "operation": "query_database",
        "referenced_tables": output.get("referenced_tables", []),
        "row_count": output.get("row_count", 0), "truncated": output.get("truncated", False),
        "query_id": output.get("query_id", fields.get("query_id")),
        **fields.get("query_quality", {}),
    }
    if result.success:
        if fields.get("sql_for_trace"):
            metadata["sql"] = fields["sql_for_trace"]
        recorder.record(run_id, TraceEventType.DATABASE_QUERY_VALIDATED, iteration=iteration, success=True, metadata=metadata)
        recorder.record(run_id, TraceEventType.DATABASE_QUERY_STARTED, iteration=iteration, metadata=metadata)
        recorder.record(run_id, TraceEventType.DATABASE_QUERY_FINISHED, iteration=iteration, duration_ms=duration_ms, success=True, metadata=metadata)
    elif result.metadata.get("failure_category") == "database_query_rejected":
        recorder.record(run_id, TraceEventType.DATABASE_QUERY_REJECTED, iteration=iteration, success=False,
                        metadata={**metadata, "failure_category": "database_query_rejected"})
    else:
        recorder.record(run_id, TraceEventType.DATABASE_QUERY_FAILED, iteration=iteration, duration_ms=duration_ms, success=False,
                        metadata={**metadata, "failure_category": result.metadata.get("failure_category", "database_query_error"), "error": result.error})


# --------------------------------------------------------------------------- analytics python


def _analytics_trace_start(
    recorder: TraceRecorder, run_id: str, iteration: int | None, fields: Fields,
    arguments: Mapping[str, Any],
) -> None:
    recorder.record(
        run_id, TraceEventType.ANALYTICS_PYTHON_STARTED, iteration=iteration,
        metadata={
            "agent": fields.get("agent"), "operation": "analyze_dataset",
            "dataset_id": arguments.get("dataset_id"),
        },
    )


def _analytics_trace_finish(
    recorder: TraceRecorder, run_id: str, fields: Fields, result: ToolResult, duration_ms: int
) -> None:
    output = _output(result)
    iteration = fields.get("iteration")
    recorder.record(
        run_id,
        TraceEventType.ANALYTICS_PYTHON_FINISHED if result.success else TraceEventType.ANALYTICS_PYTHON_FAILED,
        iteration=iteration, duration_ms=duration_ms, success=result.success,
        metadata={
            "agent": fields.get("agent"), "dataset_id": output.get("dataset_id"),
            "duration_ms": output.get("duration_ms", duration_ms),
            "failure_category": result.metadata.get("failure_category"),
        },
    )
    if not result.success:
        return
    for artifact in _artifacts(output):
        metadata = {"artifact_id": artifact.get("id"), "dataset_id": output.get("dataset_id")}
        recorder.record(run_id, TraceEventType.ARTIFACT_CREATED, iteration=iteration, success=True, metadata=metadata)
        recorder.record(run_id, TraceEventType.CHART_CREATED, iteration=iteration, success=True, metadata=metadata)


# --------------------------------------------------------------------------- reports


def _report_trace_finish(
    recorder: TraceRecorder, run_id: str, fields: Fields, result: ToolResult, duration_ms: int
) -> None:
    if not result.success:
        return
    output = _output(result)
    for artifact in _artifacts(output):
        metadata = {key: artifact.get(key) for key in ("id", "artifact_type", "name")}
        metadata["report_type"] = output.get("report_type")
        recorder.record(run_id, TraceEventType.ARTIFACT_CREATED, iteration=fields.get("iteration"), success=True, metadata=metadata)
        if artifact.get("artifact_type") == "report":
            recorder.record(run_id, TraceEventType.REPORT_CREATED, iteration=fields.get("iteration"), success=True, metadata=metadata)


OBSERVERS: tuple[ToolObserver, ...] = (
    ToolObserver(
        name="filesystem", applies=_kind("filesystem"),
        context=lambda tool, arguments: {"relative_path": arguments.get("path", "")},
        on_started=_filesystem_started, on_finished=_filesystem_finished,
    ),
    ToolObserver(
        name="command", applies=_kind("command"),
        context=lambda tool, arguments: {
            "command": arguments.get("command", ""),
            "args_summary": command_args_summary(arguments.get("args")),
        },
        on_started=_command_started, on_finished=_command_finished,
    ),
    ToolObserver(
        name="python", applies=_kind("python"),
        context=lambda tool, arguments: {"code_bytes": code_bytes(arguments.get("code"))},
        on_started=_python_started, on_finished=_python_finished,
    ),
    ToolObserver(
        name="repository", applies=_kind("repository"),
        on_started=_repository_started, on_finished=_repository_finished,
    ),
    ToolObserver(
        name="artifact", applies=_named("register_artifact"),
        on_finished=_artifact_finished, on_trace_finish=_artifact_trace,
    ),
    ToolObserver(
        name="database_schema", applies=_named(*_SCHEMA_EVENTS),
        context=lambda tool, arguments: {"database_table_names": database_table_names(tool.name, arguments)},
        on_trace_finish=_schema_trace,
    ),
    ToolObserver(
        name="sql", applies=_named("query_database"),
        context=_query_context, run_context=_query_run_context,
        on_trace_start=_query_trace_start, on_trace_finish=_query_trace_finish,
    ),
    ToolObserver(
        name="analytics_python", applies=_kind("analytics_python"),
        on_trace_start=_analytics_trace_start, on_trace_finish=_analytics_trace_finish,
    ),
    ToolObserver(
        name="report", applies=_named("generate_report"),
        on_trace_finish=_report_trace_finish,
    ),
)


def observers_for(tool: Tool) -> tuple[ToolObserver, ...]:
    """Return the observers that apply to one tool, in registration order."""

    return tuple(observer for observer in OBSERVERS if observer.applies(tool))
