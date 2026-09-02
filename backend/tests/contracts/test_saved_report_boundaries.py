"""Saving or executing a saved report definition must never call an LLM.

The only place in this application allowed to prompt a model is a normal
agent conversation turn. A saved report definition whose narrative policy
demands a new investigation is refused by the API route directly -- it never
reaches ``app.reports.execution`` at all -- so this module's own import graph
can be, and is, entirely free of ``app.llm``.
"""

import ast
from collections import deque
from pathlib import Path

import pytest

from tests.support import BACKEND_ROOT

APP = BACKEND_ROOT / "app"


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
        queue.extend(_imports(name))
    return seen


@pytest.mark.parametrize(
    "module",
    ["app.reports.contracts", "app.reports.periods", "app.reports.store", "app.reports.execution"],
)
def test_no_saved_report_module_reaches_the_llm_provider(module: str) -> None:
    reachable = _reachable(module)

    assert module in reachable
    llm_reachable = [name for name in reachable if name.startswith("app.llm")]
    assert not llm_reachable, f"{module} can reach the LLM provider package via {llm_reachable}"


def test_the_execution_service_never_imports_the_run_manager() -> None:
    """The one thing that *can* start a model turn stays firmly on the API side.

    If ``SavedReportExecutionService`` could reach ``AgentRunManager``, a
    future change could make execution start an investigation implicitly --
    exactly what the narrative-policy refusal exists to prevent.
    """

    assert "app.orchestration.run_manager" not in _reachable("app.reports.execution")


def test_a_create_request_cannot_carry_pre_written_narrative_prose_by_default() -> None:
    """A caller may only attach prose by explicitly seeding it from a real run.

    ``include_original`` is refused without a ``seed_narrative``; the field
    exists precisely so a saved report can never manufacture narrative text
    that did not come from an actual completed investigation.
    """

    from app.api.schemas.saved_reports import SavedReportCreateRequest

    fields = SavedReportCreateRequest.model_fields
    assert "seed_narrative" in fields
    with pytest.raises(ValueError):
        SavedReportCreateRequest(
            workspace_id="workspace-a", name="Weekly Revenue", template_id="analysis_summary",
            metric_requests=[{"metric": "revenue"}], default_period={"kind": "current_month"},
            narrative_policy="include_original",
        )


def test_an_update_request_carries_no_figures() -> None:
    """A caller may edit parameters and presentation, never a factual value.

    There is no field on the update contract that lets a client hand back a
    number to display as-is; every figure a saved report shows comes from a
    metric rerun the server itself executes.
    """

    from app.api.schemas.saved_reports import SavedReportUpdateRequest

    fields = SavedReportUpdateRequest.model_fields
    for name in ("name", "description", "template_id", "narrative_policy", "status"):
        annotation = str(fields[name].annotation)
        assert "int" not in annotation and "float" not in annotation, (
            f"{name} accepts a numeric value from the frontend"
        )
    with pytest.raises(ValueError):
        SavedReportUpdateRequest(expected_version=1, revenue=163)
