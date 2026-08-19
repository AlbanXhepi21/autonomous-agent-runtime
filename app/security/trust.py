"""Runtime-owned provenance and lightweight prompt-injection diagnostics."""

import re
from collections.abc import Mapping
from typing import Any

from app.security.models import ContentTrust, UntrustedContent

_INDICATORS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ignore_previous_instructions", re.compile(r"ignore (?:all )?(?:previous|prior) instructions", re.I)),
    ("reveal_system_prompt", re.compile(r"reveal (?:the )?(?:system prompt|instructions)", re.I)),
    ("send_secrets", re.compile(r"(?:send|reveal|exfiltrate).{0,40}(?:api[_ -]?key|secret|password|token)", re.I)),
    ("disable_security", re.compile(r"(?:disable|bypass|ignore).{0,40}(?:security|policy|approval)", re.I)),
    ("run_command", re.compile(r"(?:run|execute) (?:this )?command", re.I)),
)


def external_content_for_tool(tool_name: str, arguments: Mapping[str, Any], output: Any) -> UntrustedContent | None:
    """Classify content-bearing tool output without trusting caller-controlled labels."""

    if tool_name == "read_file":
        return UntrustedContent(content=output, source=str(arguments.get("path", "workspace file")),
                                source_type="filesystem", trust=ContentTrust.UNTRUSTED_EXTERNAL)
    if tool_name in {"get_repository_tree", "search_files", "git_inspect"}:
        return UntrustedContent(content=output, source="workspace repository", source_type="repository",
                                trust=ContentTrust.UNTRUSTED_EXTERNAL)
    if tool_name == "web_search":
        return UntrustedContent(content=output, source="web search", source_type="web",
                                trust=ContentTrust.UNTRUSTED_EXTERNAL)
    return None


def injection_indicators(content: Any) -> tuple[str, ...]:
    """Return bounded heuristic matches for diagnostics, never an authorization result."""

    text = _text(content)[:20_000]
    return tuple(identifier for identifier, pattern in _INDICATORS if pattern.search(text))


def _text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(_text(item) for item in value.values())
    if isinstance(value, list | tuple):
        return " ".join(_text(item) for item in value)
    return value if isinstance(value, str) else ""
