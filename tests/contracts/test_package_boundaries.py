"""Structural rules about which packages may import which.

A cycle between two packages means neither can be understood, tested or
extracted without the other. These rules are cheap to satisfy while the graph
is acyclic and expensive to restore once it is not, so they are asserted rather
than documented.
"""

import ast
from collections import defaultdict
from pathlib import Path
from tests.support import REPO_ROOT

APP = REPO_ROOT / "app"

# Packages that exist to be depended on, and so may not depend on the runtime.
LEAF_PACKAGES = {"contracts", "core"}


def package_of(path: Path) -> str:
    """Return the top-level app package a module belongs to."""

    relative = path.relative_to(APP)
    return relative.parts[0] if len(relative.parts) > 1 else relative.stem


def imported_packages(path: Path) -> set[str]:
    """Return the top-level app packages a module imports from."""

    tree = ast.parse(path.read_text(), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app."):
            found.add(node.module.split(".")[1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app."):
                    found.add(alias.name.split(".")[1])
    return found


def import_graph() -> dict[str, set[str]]:
    """Build the package-to-package import graph, ignoring self-edges."""

    graph: dict[str, set[str]] = defaultdict(set)
    for path in APP.rglob("*.py"):
        source = package_of(path)
        graph[source] |= {p for p in imported_packages(path) if p != source}
    return graph


def find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Return each import cycle as the path of packages that forms it."""

    cycles: list[list[str]] = []
    seen: set[str] = set()

    def walk(node: str, path: list[str], visiting: set[str]) -> None:
        for target in sorted(graph.get(node, ())):
            if target in visiting:
                cycle = path[path.index(target):] + [target]
                if (key := tuple(sorted(set(cycle)))) not in seen:
                    seen.add(key)
                    cycles.append(cycle)
            elif target not in path:
                walk(target, path + [target], visiting | {target})

    for start in sorted(graph):
        walk(start, [start], {start})
    return cycles


def test_no_package_import_cycles() -> None:
    cycles = find_cycles(import_graph())

    assert not cycles, "Import cycles: " + "; ".join(" -> ".join(c) for c in cycles)


def test_leaf_packages_do_not_depend_on_the_runtime() -> None:
    graph = import_graph()

    offenders = {
        package: sorted(graph.get(package, set()) - LEAF_PACKAGES)
        for package in LEAF_PACKAGES
        if graph.get(package, set()) - LEAF_PACKAGES
    }

    assert not offenders, f"Leaf packages may only import each other: {offenders}"


def test_provider_and_storage_packages_do_not_import_the_runtime() -> None:
    """llm, security and memory describe what they consume via contracts."""

    graph = import_graph()

    importers = sorted(p for p in ("llm", "security", "memory") if "agent" in graph.get(p, set()))

    assert not importers, (
        f"{importers} import app.agent, which is the cycle contracts/ exists to prevent."
    )
