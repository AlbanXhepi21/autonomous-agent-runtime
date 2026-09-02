"""Deterministic suitability scoring and template recommendation."""

from app.analytics.presentation.assignment import assign_slots
from app.analytics.presentation.charts import ChartSpec, KPIItem
from app.analytics.presentation.suitability import recommend_template, score_assignment
from app.analytics.presentation.templates import ReportTemplate, TemplateBlock, TemplateSlot
from app.contracts.answers import AnswerSource


def bar_chart(chart_id: str, query_id: str = "query_001") -> ChartSpec:
    return ChartSpec(
        id=chart_id, type="bar", title="Breakdown", x_field="category", y_fields=["value"],
        data=[{"category": "A", "value": 1}, {"category": "B", "value": 2}], source_query_ids=[query_id],
    )


def kpi_chart(chart_id: str, items: int, query_id: str = "query_001") -> ChartSpec:
    return ChartSpec(
        id=chart_id, type="kpi", title="Headline", source_query_ids=[query_id],
        kpis=[KPIItem(label=f"Metric {i}", value=str(i)) for i in range(items)],
    )


def slot(slot_id: str, accepts: list[str], **overrides: object) -> TemplateSlot:
    defaults = {"minimum": 0, "maximum": 1, "required": False, "role": "primary"}
    defaults.update(overrides)
    return TemplateSlot(id=slot_id, accepts=accepts, **defaults)


def template(name: str, *, slots: list[TemplateSlot]) -> ReportTemplate:
    return ReportTemplate(
        name=name, title=name, description="A template for testing.", report_type="executive",
        period_granularity="custom", blocks=[TemplateBlock(kind="cover")], slots=slots,
    )


def source(query_id: str) -> AnswerSource:
    return AnswerSource(id=query_id, run_id="r1", label=query_id)


def test_completion_percentage_is_the_required_slot_satisfaction_ratio() -> None:
    t = template("t", slots=[
        slot("a", ["bar"], minimum=1, required=True),
        slot("b", ["kpi"], minimum=1, required=True),
    ])
    assignment = assign_slots(t, [bar_chart("c1")], [source("query_001")])

    suitability = score_assignment(assignment)

    assert suitability.completion_percentage == 50.0
    assert suitability.satisfied_required_slots == ["a"]
    assert suitability.missing_required_slots == ["b"]
    assert not suitability.can_publish


def test_completion_percentage_is_100_when_there_are_no_required_slots() -> None:
    t = template("t", slots=[slot("a", ["bar"], required=False)])
    assignment = assign_slots(t, [], [])

    suitability = score_assignment(assignment)

    assert suitability.completion_percentage == 100.0
    assert suitability.can_publish


def test_can_publish_is_true_once_every_required_slot_is_satisfied() -> None:
    t = template("t", slots=[
        slot("a", ["bar"], minimum=1, required=True),
        slot("b", ["kpi"], minimum=1, required=False),
    ])
    assignment = assign_slots(t, [bar_chart("c1")], [source("query_001")])

    suitability = score_assignment(assignment)

    assert suitability.completion_percentage == 100.0
    assert suitability.can_publish
    assert suitability.optional_slots_total == 1
    assert suitability.optional_slots_filled == 0


def test_warnings_report_unused_and_unresolved_evidence_displays() -> None:
    t = template("t", slots=[slot("a", ["bar"], maximum=1)])
    used = bar_chart("c1", "query_001")
    unused = bar_chart("c2", "query_002")
    unresolved = bar_chart("c3", "query_999")
    assignment = assign_slots(t, [used, unused, unresolved], [source("query_001"), source("query_002")])

    suitability = score_assignment(assignment)

    assert any("not used" in warning for warning in suitability.warnings)
    assert any("outside this run's resolved citations" in warning for warning in suitability.warnings)
    assert suitability.unused_display_count == 1


def test_recommend_template_prefers_higher_completion_percentage() -> None:
    complete = template("complete", slots=[slot("a", ["bar"], minimum=1, required=True)])
    incomplete = template("incomplete", slots=[slot("a", ["bar"], minimum=1, required=True), slot("b", ["kpi"], minimum=1, required=True)])
    charts, sources = [bar_chart("c1")], [source("query_001")]

    items = [score_assignment(assign_slots(t, charts, sources)) for t in (complete, incomplete)]

    assert recommend_template(items) == "complete"


def test_recommend_template_breaks_a_completion_tie_on_optional_slots_filled() -> None:
    plain = template("plain", slots=[])
    with_optional = template("with_optional", slots=[slot("a", ["bar"], required=False)])
    charts, sources = [bar_chart("c1")], [source("query_001")]

    items = [score_assignment(assign_slots(t, charts, sources)) for t in (plain, with_optional)]

    assert recommend_template(items) == "with_optional"


def test_recommend_template_falls_back_to_template_name_for_a_full_tie() -> None:
    a = template("alpha", slots=[])
    b = template("beta", slots=[])

    items = [score_assignment(assign_slots(t, [], [])) for t in (a, b)]

    assert recommend_template(items) == "alpha"


def test_recommend_template_returns_none_for_no_templates() -> None:
    assert recommend_template([]) is None


def test_a_small_run_favors_a_template_with_no_required_slots() -> None:
    """The shape of `test_analysis_summary_recommended_for_a_small_run` in miniature."""

    lenient = template("analysis_summary", slots=[slot("charts", ["bar", "line"], required=False, maximum=6)])
    demanding = template("executive_dashboard", slots=[
        slot("headline_metrics", ["kpi"], minimum=3, maximum=6, required=True),
        slot("primary_breakdown", ["bar", "stacked_bar"], minimum=1, required=True),
    ])
    charts, sources = [bar_chart("c1")], [source("query_001")]

    items = [score_assignment(assign_slots(t, charts, sources)) for t in (lenient, demanding)]

    assert recommend_template(items) == "analysis_summary"
