"""Structural guarantees for workspaces and memberships.

Mirrors ``tests/contracts/test_identity_boundaries.py``: ``app.tenancy``
must never reach ``app.agent`` (the runtime execution package) or
``app.security`` (agent tool-capability policy -- a different "permission"
system this package must not be conflated with). It's expected, and
unrestricted, for ``app.tenancy`` to reach ``app.identity`` -- a membership
is meaningless without a user. The reverse must never happen:
``app.identity`` has no reason to know workspaces exist.
"""

from __future__ import annotations

import ast
from collections import deque
from pathlib import Path

from tests.support import BACKEND_ROOT

APP = BACKEND_ROOT / "app"

TENANCY_ENTRYPOINTS = (
    "app.tenancy.contracts",
    "app.tenancy.permissions",
    "app.tenancy.context",
    "app.tenancy.store",
    "app.tenancy.service",
)
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


def test_tenancy_never_imports_the_agent_runtime() -> None:
    for entrypoint in TENANCY_ENTRYPOINTS:
        reachable = _reachable(entrypoint)
        offenders = {module for module in reachable if module.startswith("app.agent")}
        assert not offenders, f"{entrypoint} reaches app.agent via {offenders}"


def test_tenancy_never_imports_agent_tool_capability_policy() -> None:
    for entrypoint in TENANCY_ENTRYPOINTS:
        reachable = _reachable(entrypoint)
        offenders = {module for module in reachable if module.startswith("app.security")}
        assert not offenders, f"{entrypoint} reaches app.security via {offenders}"


def test_identity_never_imports_tenancy() -> None:
    """The dependency direction is one-way: tenancy depends on identity, never
    the reverse. Reversing it would create the exact import cycle risk
    ``tests/contracts/test_package_boundaries.py`` exists to catch.
    """

    for entrypoint in IDENTITY_ENTRYPOINTS:
        reachable = _reachable(entrypoint)
        offenders = {module for module in reachable if module.startswith("app.tenancy")}
        assert not offenders, f"{entrypoint} reaches app.tenancy via {offenders}"


def test_tenancy_contracts_is_a_leaf_module() -> None:
    """Workspace/Membership/Invitation/Role/MembershipStatus must import no
    other ``app`` module at all.
    """

    imports = _imports("app.tenancy.contracts")

    assert not imports, f"app.tenancy.contracts imports: {imports}"


def test_tenancy_permissions_only_depends_on_tenancy_contracts() -> None:
    """The Permission enum and ROLE_PERMISSIONS mapping should need nothing
    beyond the Role type they're keyed on.
    """

    imports = _imports("app.tenancy.permissions")

    assert imports <= {"app.tenancy.contracts"}, f"app.tenancy.permissions imports: {imports}"
