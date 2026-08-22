"""Small deterministic policies used by the agent runtime."""

import hashlib
import json
from typing import Any


def tool_action_fingerprint(tool_name: str, arguments: dict[str, Any]) -> str:
    """Return a stable fingerprint for a tool request.

    Canonical JSON makes equivalent mappings produce the same value regardless
    of their original key order.
    """

    canonical_action = json.dumps(
        {"tool_name": tool_name, "arguments": arguments},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical_action.encode("utf-8")).hexdigest()


def delegation_fingerprint(agent_name: str, objective: str, context: str | None) -> str:
    """Return a stable fingerprint for a bounded delegation request."""

    canonical_request = json.dumps(
        {"agent_name": agent_name, "objective": objective, "context": context},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
