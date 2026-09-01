"""Bounded, non-sensitive projections of tool arguments for logs and traces.

Execution events must describe what happened without carrying file content,
command arguments, source text or query text into the log or the trace.
"""

from collections.abc import Mapping
from hashlib import sha256
from typing import Any


def safe_logged_arguments(
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
    if tool_name == "query_database":
        sql = arguments.get("sql")
        return {"sql": f"[{len(sql.encode('utf-8'))} bytes of SQL]" if isinstance(sql, str) else "[invalid SQL]"}
    if tool_name != "write_file":
        return arguments
    return {
        key: "[OMITTED FILE CONTENT]" if key == "content" else value
        for key, value in arguments.items()
    }


def command_args_summary(args: Any) -> str:
    """Record only argv cardinality; command arguments may contain sensitive values."""

    return f"{len(args)} arguments" if isinstance(args, list) else "0 arguments"


def code_bytes(code: Any) -> int:
    """Report source size without retaining source text in execution events."""

    return len(code.encode("utf-8")) if isinstance(code, str) else 0


def database_table_names(tool_name: object, arguments: object) -> list[str]:
    """Extract only safe table identifiers for database trace events."""

    if not isinstance(arguments, Mapping):
        return []
    names = arguments.get("table_names")
    if isinstance(names, list):
        return [item for item in names if isinstance(item, str)]
    if tool_name in {"describe_table", "get_table_relationships"} and isinstance(arguments.get("table_name"), str):
        return [arguments["table_name"]]
    return []


def query_purpose(purpose: Any) -> str | None:
    """Keep the model's short description of a query, bounded, never its SQL."""

    if not isinstance(purpose, str) or not purpose.strip():
        return None
    return purpose.strip()[:200]


def query_quality_metadata(sql: Any) -> dict[str, object]:
    """Expose only coarse SQL-quality signals to evaluations, never query text."""

    if not isinstance(sql, str):
        return {}
    compact = " ".join(sql.lower().split())
    return {
        "query_fingerprint": sha256(compact.encode("utf-8")).hexdigest()[:16],
        "select_star": "select *" in compact,
        "has_limit": " limit " in f" {compact} ",
        "raw_event_query": "web_events" in compact and "group by" not in compact,
    }


def safe_sql_for_trace(sql: Any, max_chars: int) -> str | None:
    """Keep SQL only for an explicitly enabled, bounded developer trace."""

    if not isinstance(sql, str) or max_chars <= 0:
        return None
    return sql[:max_chars]
