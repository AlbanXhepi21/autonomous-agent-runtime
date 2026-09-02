"""Deterministic assignment of a run's displays into a template's slots."""

from app.analytics.presentation.assignment import assign_slots
from app.analytics.presentation.charts import ChartSpec, KPIItem
from app.analytics.presentation.templates import ReportTemplate, TemplateBlock, TemplateSlot
from app.contracts.answers import AnswerSource


def kpi_chart(chart_id: str, *, items: int = 1, query_id: str = "query_001", title: str = "Headline") -> ChartSpec:
    return ChartSpec(
        id=chart_id, type="kpi", title=title, source_query_ids=[query_id],
        kpis=[KPIItem(label=f"Metric {i}", value=str(i)) for i in range(items)],
    )


def bar_chart(chart_id: str, *, query_id: str = "query_001", title: str = "Breakdown", description: str | None = None) -> ChartSpec:
    return ChartSpec(
        id=chart_id, type="bar", title=title, description=description, x_field="category", y_fields=["value"],
        data=[{"category": "A", "value": 1}, {"category": "B", "value": 2}], source_query_ids=[query_id],
    )


def line_chart(chart_id: str, *, query_id: str = "query_001", title: str = "Trend") -> ChartSpec:
    return ChartSpec(
        id=chart_id, type="line", title=title, x_field="month", y_fields=["value"],
        data=[{"month": "2026-01", "value": 1}, {"month": "2026-02", "value": 2}], source_query_ids=[query_id],
    )


def table_chart(chart_id: str, *, query_id: str = "query_001", title: str = "Rows") -> ChartSpec:
    return ChartSpec(id=chart_id, type="table", title=title, data=[{"a": 1}], source_query_ids=[query_id])


def source(query_id: str) -> AnswerSource:
    return AnswerSource(id=query_id, run_id="r1", label=query_id)


def slot(slot_id: str, accepts: list[str], **overrides: object) -> TemplateSlot:
    defaults = {"minimum": 0, "maximum": 1, "required": False, "role": "primary"}
    defaults.update(overrides)
    return TemplateSlot(id=slot_id, accepts=accepts, **defaults)


def template(*, slots: list[TemplateSlot]) -> ReportTemplate:
    return ReportTemplate(
        name="t", title="T", description="A template for testing.", report_type="executive",
        period_granularity="custom", blocks=[TemplateBlock(kind="cover")], slots=slots,
    )


def test_assignment_prefers_purpose_hint_then_falls_back_to_creation_order() -> None:
    revenue = bar_chart("c1", query_id="query_001", title="Revenue by category")
    refunds = bar_chart("c2", query_id="query_002", title="Refunds by reason")
    t = template(slots=[slot("breakdown", ["bar"], maximum=1, purpose_hint="refund")])

    result = assign_slots(t, [revenue, refunds], [source("query_001"), source("query_002")])

    assert result.slots[0].assigned_chart_ids == ["c2"]


def test_assignment_falls_back_to_creation_order_without_a_hint_match() -> None:
    first = bar_chart("c1", query_id="query_001")
    second = bar_chart("c2", query_id="query_002")
    t = template(slots=[slot("breakdown", ["bar"], maximum=1)])

    result = assign_slots(t, [first, second], [source("query_001"), source("query_002")])

    assert result.slots[0].assigned_chart_ids == ["c1"]


def test_a_display_is_never_assigned_to_two_slots() -> None:
    chart = bar_chart("c1", query_id="query_001")
    t = template(slots=[
        slot("first", ["bar"], maximum=1),
        slot("second", ["bar", "stacked_bar"], maximum=1),
    ])

    result = assign_slots(t, [chart], [source("query_001")])

    assert result.slots[0].assigned_chart_ids == ["c1"]
    assert result.slots[1].assigned_chart_ids == []
    assert result.unused_chart_ids == []


def test_assignment_order_is_stable_across_repeated_calls() -> None:
    charts = [bar_chart(f"c{i}", query_id=f"query_{i:03d}") for i in range(1, 5)]
    sources = [source(f"query_{i:03d}") for i in range(1, 5)]
    t = template(slots=[slot("breakdown", ["bar"], minimum=1, maximum=3)])

    first = assign_slots(t, charts, sources)
    second = assign_slots(t, charts, sources)

    assert first.model_dump() == second.model_dump()
    assert first.slots[0].assigned_chart_ids == ["c1", "c2", "c3"]
    assert first.unused_chart_ids == ["c4"]


def test_unresolved_evidence_is_excluded_from_every_slot() -> None:
    known = bar_chart("c1", query_id="query_001")
    unknown = bar_chart("c2", query_id="query_999")
    t = template(slots=[slot("breakdown", ["bar"], minimum=1, maximum=5)])

    result = assign_slots(t, [known, unknown], [source("query_001")])

    assert result.slots[0].assigned_chart_ids == ["c1"]
    assert result.unresolved_evidence_chart_ids == ["c2"]
    assert result.unused_chart_ids == []


def test_a_kpi_slot_counts_individual_metrics_not_charts() -> None:
    headline = kpi_chart("c1", items=4, query_id="query_001")
    t = template(slots=[slot("headline", ["kpi"], minimum=3, maximum=6, required=True)])

    result = assign_slots(t, [headline], [source("query_001")])

    assert result.slots[0].assigned_chart_ids == ["c1"]
    assert result.slots[0].satisfied


def test_a_kpi_slot_is_unsatisfied_with_too_few_metrics() -> None:
    headline = kpi_chart("c1", items=2, query_id="query_001")
    t = template(slots=[slot("headline", ["kpi"], minimum=3, maximum=6, required=True)])

    result = assign_slots(t, [headline], [source("query_001")])

    assert not result.slots[0].satisfied


def test_a_display_beyond_the_slot_maximum_is_left_unused() -> None:
    charts = [bar_chart(f"c{i}", query_id=f"query_{i:03d}") for i in range(1, 4)]
    sources = [source(f"query_{i:03d}") for i in range(1, 4)]
    t = template(slots=[slot("breakdown", ["bar"], maximum=2)])

    result = assign_slots(t, charts, sources)

    assert result.slots[0].assigned_chart_ids == ["c1", "c2"]
    assert result.unused_chart_ids == ["c3"]


def test_a_lone_oversized_kpi_display_is_still_taken_whole() -> None:
    """A display's units are never split, even past the slot's own maximum."""

    headline = kpi_chart("c1", items=8, query_id="query_001")
    t = template(slots=[slot("headline", ["kpi"], minimum=3, maximum=6, required=True)])

    result = assign_slots(t, [headline], [source("query_001")])

    assert result.slots[0].assigned_chart_ids == ["c1"]
    assert result.slots[0].satisfied


def test_a_required_slot_with_no_eligible_display_is_unsatisfied() -> None:
    t = template(slots=[slot("headline", ["kpi"], minimum=1, required=True)])

    result = assign_slots(t, [bar_chart("c1")], [source("query_001")])

    assert result.slots[0].assigned_chart_ids == []
    assert not result.slots[0].satisfied


def test_content_order_concatenates_slots_in_declared_order() -> None:
    trend = line_chart("c1", query_id="query_001")
    breakdown = bar_chart("c2", query_id="query_002")
    t = template(slots=[
        slot("trend", ["line", "area"], maximum=1),
        slot("breakdown", ["bar", "stacked_bar"], maximum=1),
    ])

    result = assign_slots(t, [breakdown, trend], [source("query_001"), source("query_002")])

    assert result.content_order() == {"chart": ["c1", "c2"]}


def test_content_order_groups_by_block_kind() -> None:
    headline = kpi_chart("c1", items=3, query_id="query_001")
    trend = line_chart("c2", query_id="query_002")
    rows = table_chart("c3", query_id="query_003")
    t = template(slots=[
        slot("headline", ["kpi"], minimum=1, maximum=6),
        slot("trend", ["line", "area"], maximum=1),
        slot("rows", ["table"], maximum=1),
    ])

    result = assign_slots(t, [headline, trend, rows], [source("query_001"), source("query_002"), source("query_003")])

    assert result.content_order() == {"metrics": ["c1"], "chart": ["c2"], "table": ["c3"]}


def test_a_template_with_no_slots_assigns_nothing_and_leaves_all_displays_unused() -> None:
    t = template(slots=[])

    result = assign_slots(t, [bar_chart("c1", query_id="query_001")], [source("query_001")])

    assert result.slots == []
    assert result.unused_chart_ids == ["c1"]
