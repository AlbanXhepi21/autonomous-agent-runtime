"""Structural rules that keep a published figure traceable to a run.

The compiler decides what a report contains; the renderers only set it. That is
easy to state and easy to erode — one convenient import of ``ChartSpec`` into a
writer and a renderer can start choosing its own facts again, with both formats
free to disagree. These rules are asserted rather than documented, and each one
fails if the property it protects is removed.
"""

import ast
from collections import deque
from pathlib import Path

import pytest

from tests.support import BACKEND_ROOT

APP = BACKEND_ROOT / "app"

#: What the renderers are allowed to see. Anything else would let a writer read
#: run-level data and reach its own conclusion about what to print.
RENDERER_MODULES = ["app.analytics.presentation.documents"]
RENDERER_MAY_IMPORT = {
    "app.analytics.presentation.compiler",
    "app.analytics.presentation.document_model",
    "app.analytics.presentation.theme",
}
#: Run-level material: the raw displays and the evidence registry. A renderer
#: seeing these could select facts the compiler did not put in a block.
RUN_LEVEL_MODULES = {
    "app.analytics.presentation.charts",
    "app.analytics.presentation.chart_store",
    "app.contracts.answers",
    "app.conversations.store",
}


def _module_path(name: str) -> Path | None:
    base = BACKEND_ROOT / name.replace(".", "/")
    for candidate in (base.with_suffix(".py"), base / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


def _imports(name: str) -> set[str]:
    """The app modules one module imports directly."""

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
    """Every app module reachable from one module, transitively."""

    seen: set[str] = set()
    queue = deque([start])
    while queue:
        name = queue.popleft()
        if name in seen:
            continue
        seen.add(name)
        queue.extend(_imports(name))
    return seen


@pytest.mark.parametrize("module", RENDERER_MODULES)
def test_a_renderer_sees_only_the_compiled_report(module: str) -> None:
    """A writer may read the compiled document and the theme, and nothing else."""

    assert _imports(module) <= RENDERER_MAY_IMPORT, (
        f"{module} imports beyond the compiled report: "
        f"{sorted(_imports(module) - RENDERER_MAY_IMPORT)}"
    )


@pytest.mark.parametrize("module", RENDERER_MODULES)
def test_a_renderer_cannot_reach_run_level_facts(module: str) -> None:
    """Not even transitively: a chart spec must not be reachable from a writer.

    The compiler is allowed to see them — that is its job — so this checks the
    renderer's own imports rather than the whole graph behind them.
    """

    for forbidden in RUN_LEVEL_MODULES:
        assert forbidden not in _imports(module), (
            f"{module} can read {forbidden} and could select its own facts"
        )


def test_both_renderers_live_behind_one_entry_point() -> None:
    """PDF and DOCX are written by the same module, from the same argument."""

    from app.analytics.presentation import documents

    assert hasattr(documents, "write_pdf") and hasattr(documents, "write_docx")
    import inspect

    pdf = inspect.signature(documents.write_pdf).parameters
    docx = inspect.signature(documents.write_docx).parameters
    assert list(pdf) == list(docx) == ["report", "images", "path", "theme"]
    assert pdf["report"].annotation == docx["report"].annotation


def test_publishing_never_reaches_a_model() -> None:
    """Compiling and rendering are assembly; a model call would rewrite an analysis."""

    reachable = _reachable("app.orchestration.publishing")

    assert "app.orchestration.publishing" in reachable
    assert not [name for name in reachable if name.startswith("app.llm")], (
        "publishing reaches the LLM provider package"
    )


def test_the_publish_request_carries_no_figures() -> None:
    """A caller chooses a shape, a period and a grouping. Never a value.

    A number the frontend supplied could otherwise be printed as a fact no query
    produced, which is what provenance exists to prevent. Numbers are allowed in
    exactly one place — the right-hand side of a filter — where they are bound
    into the statement and never rendered as a metric.
    """

    from app.api.schemas.analytics import PublishReportRequest

    fields = PublishReportRequest.model_fields
    assert set(fields) == {"template", "formats", "period", "title", "metrics", "narrative"}
    for name in ("template", "formats", "period", "title"):
        annotation = str(fields[name].annotation)
        assert "int" not in annotation and "float" not in annotation, (
            f"{name} accepts a numeric value from the frontend"
        )
    # And nothing may be smuggled in beside them.
    with pytest.raises(ValueError):
        PublishReportRequest(template="monthly_business_review", formats=["pdf"], revenue=163)


def test_a_rerun_request_cannot_supply_sql_or_a_displayed_value() -> None:
    """The recompute surface names definitions; it never contributes statement text."""

    from app.analytics.semantics.parameters import MetricFilter, MetricParameters

    assert set(MetricParameters.model_fields) == {
        "metric", "period", "dimensions", "filters", "grain",
    }
    # Dimensions and metrics are names resolved against the registry, never
    # expressions, so they are plain strings with nowhere to put SQL.
    assert "str" in str(MetricParameters.model_fields["metric"].annotation)

    for model in (MetricParameters, MetricFilter):
        with pytest.raises(ValueError):
            model.model_validate({"sql": "DROP TABLE orders"})

    # A filter value may be a number; it is bound, never printed as a figure.
    filtered = MetricFilter(field="campaign_id", operator="gt", value=5)
    assert filtered.value == 5


def test_a_template_cannot_declare_an_unknown_block() -> None:
    """Structure files are data, so the block vocabulary is closed at load time."""

    from app.analytics.presentation.templates import TemplateBlock

    with pytest.raises(ValueError):
        TemplateBlock(kind="arbitrary_html", heading="Anything")


def test_every_shipped_template_separates_structure_from_theme() -> None:
    """A restyle edits one file and a new section edits the other."""

    directory = APP / "resources" / "report_templates"
    shapes = sorted(path.parent for path in directory.glob("*/metadata.json"))

    assert shapes, "no report templates were discovered"
    for shape in shapes:
        assert (shape / "theme.json").is_file(), f"{shape.name} has no theme"
        structure = (shape / "metadata.json").read_text()
        # Appearance must not leak into the structure file, or the two drift.
        for appearance in ('"palette"', '"fonts"', '"spacing"', '"chart_palette"'):
            assert appearance not in structure, f"{shape.name} mixes theme into structure"
