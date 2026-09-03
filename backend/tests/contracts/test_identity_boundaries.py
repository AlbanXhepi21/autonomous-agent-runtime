"""Structural guarantees for user identity and authentication.

``app.identity`` describes what it consumes via contracts, the same
discipline ``tests/contracts/test_package_boundaries.py`` already enforces
for ``app.llm``, ``app.security`` and ``app.memory``: none of them may reach
``app.agent``, the runtime execution package. Identity has an additional
reason to hold that line -- it is also never allowed to reach
``app.security``, which is a *different* "permission" system (agent tool
capability policy, not HTTP user authorization) that this package must not
be conflated with.
"""

from __future__ import annotations

import ast
from collections import deque
from pathlib import Path

from tests.support import BACKEND_ROOT

APP = BACKEND_ROOT / "app"
IDENTITY_ENTRYPOINTS = (
    "app.identity.contracts",
    "app.identity.passwords",
    "app.identity.tokens",
    "app.identity.rate_limit",
    "app.identity.email",
    "app.identity.store",
    "app.identity.service",
)


def _module_path(name: str) -> Path | None:
    base = BACKEND_ROOT / name.replace(".", "/")
    for candidate in (base.with_suffix(".py"), base / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


def _imports(name: str) -> set[str]:
    path = _module_path(name)
    if path is None:
        return set()
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app."):
            found.add(node.module)
        elif isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names if alias.name.startswith("app.")}
    return found


def _reachable(start: str) -> set[str]:
    seen: set[str] = set()
    queue = deque([start])
    while queue:
        name = queue.popleft()
        if name in seen:
            continue
        seen.add(name)
        queue.extend(_imports(name) - seen)
    return seen


def test_identity_never_imports_the_agent_runtime() -> None:
    for entrypoint in IDENTITY_ENTRYPOINTS:
        reachable = _reachable(entrypoint)
        offenders = {module for module in reachable if module.startswith("app.agent")}
        assert not offenders, f"{entrypoint} reaches app.agent via {offenders}"


def test_identity_never_imports_agent_tool_capability_policy() -> None:
    """app.security governs what an LLM tool call may do -- a different kind
    of "permission" from workspace roles. Conflating the two modules would
    make a future reader ask "capability of what, exactly?"
    """

    for entrypoint in IDENTITY_ENTRYPOINTS:
        reachable = _reachable(entrypoint)
        offenders = {module for module in reachable if module.startswith("app.security")}
        assert not offenders, f"{entrypoint} reaches app.security via {offenders}"


def test_identity_contracts_is_a_leaf_module() -> None:
    """The domain types (User, Session, IdentityToken) must import no other
    ``app`` module at all, so nothing depends on them by accident.
    """

    imports = _imports("app.identity.contracts")

    assert not imports, f"app.identity.contracts imports: {imports}"
