"""Render user-readable metric documentation from the canonical definitions.

Every fact in the rendered page is read from ``MetricDefinition`` — the same
object the compiler, the API and the agent's ``describe_metric`` tool all read
from. Nothing here is typed twice: there is no second, hand-maintained prose
description of what a metric means to drift out of sync with its SQL. Running
this generator again after a definition changes reproduces the checked-in
file exactly; `tests/contracts/test_metrics_doc_snapshot.py` fails otherwise.
"""

from __future__ import annotations

from app.analytics.semantics.metrics import MetricDefinition, MetricRegistry

_STATUS_LABELS = {
    "documented": "Documented (guidance only — the agent writes its own SQL)",
    "executable": "Executable (compiles and runs; not yet proven by a correctness test suite)",
    "validated": "Validated (proven against its written definition by a fixture-based test suite)",
    "production_ready": "Production ready (validated, and already relied on elsewhere in the system)",
}


def _dimension_lines(definition: MetricDefinition) -> list[str]:
    if not definition.dimension_specs:
        return ["- _None. This metric does not support grouping by a dimension._"]
    return [
        f"- `{name}` — {spec.label}"
        for name, spec in sorted(definition.dimension_specs.items())
    ]


def _filter_lines(definition: MetricDefinition) -> list[str]:
    if not definition.filter_specs:
        return ["- _None. This metric does not support filtering._"]
    lines = []
    for name, spec in sorted(definition.filter_specs.items()):
        operators = ", ".join(spec.operators)
        lines.append(f"- `{name}` — {spec.label} ({spec.value_type}; operators: {operators})")
    return lines


def _render_one(definition: MetricDefinition) -> str:
    lines = [
        f"## {definition.display_name}",
        "",
        f"**Identifier:** `{definition.identifier}`  ",
        f"**Status:** {_STATUS_LABELS[definition.status]}  ",
        f"**Unit / format:** {definition.unit} ({definition.format})",
        "",
        "### Definition",
        "",
        definition.formula,
        "",
        "### Required tables",
        "",
        ", ".join(f"`{table}`" for table in definition.required_tables) or "_None declared._",
        "",
        "### Supported time grains",
        "",
        ", ".join(f"`{grain}`" for grain in definition.supported_grains) or "_Not applicable._",
        "",
        "### Allowed dimensions",
        "",
        *_dimension_lines(definition),
        "",
        "### Allowed filters",
        "",
        *_filter_lines(definition),
        "",
        "### Result columns",
        "",
        (", ".join(f"`{column}`" for column in definition.value_columns) if definition.is_rerunnable
         else "_Not compiled; the agent's own query result columns apply instead._"),
        "",
        "### Inclusion, exclusion, null and zero-denominator behavior",
        "",
    ]
    if definition.business_caveats:
        lines.extend(f"- {caveat}" for caveat in definition.business_caveats)
    else:
        lines.append("_No stated caveats._")
    lines.append("")
    return "\n".join(lines)


def render_metrics_markdown(registry: MetricRegistry) -> str:
    """The full metrics reference, one section per definition, alphabetical by name."""

    header = [
        "# Business Metric Reference",
        "",
        "Generated from `app/analytics/semantics/metrics.py` by "
        "`python -m scripts.generate_metrics_doc`. Do not hand-edit: every fact below is read "
        "from the same typed `MetricDefinition` the compiler, the `/api/v1/analytics/metrics` "
        "endpoint and the agent's `describe_metric` tool all read from, so this file cannot "
        "state something the running system disagrees with.",
        "",
        "A metric's **status** says what a reader may do with it. `documented` metrics are "
        "guidance the agent reads before writing its own SQL, which is then validated the same "
        "way as any other agent-authored query; they are never offered as something a reader "
        "may rerun by changing report parameters. `executable`, `validated` and "
        "`production_ready` metrics compile to a statement a reader may rerun directly — see "
        "`GET /api/v1/analytics/metrics`.",
        "",
    ]
    sections = [_render_one(definition) for definition in registry.list_metrics()]
    return "\n".join(header) + "\n" + "\n".join(sections)
