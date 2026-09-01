import pytest
from pydantic import ValidationError

from app.analytics.presentation.charts import ChartSpec


def test_chart_spec_validates_bounded_data_and_fields() -> None:
    chart = ChartSpec(type="line", title="Monthly revenue", x_field="month", y_fields=["revenue"], data=[{"month": "2026-01", "revenue": 12}, {"month": "2026-02", "revenue": 14}], source_query_ids=["query_001"])
    assert chart.type == "line"
    with pytest.raises(ValidationError, match="absent"):
        ChartSpec(type="bar", title="Bad", x_field="category", y_fields=["revenue"], data=[{"category": "A"}, {"category": "B"}], source_query_ids=["query_001"])
    with pytest.raises(ValidationError):
        ChartSpec(type="line", title="Too many", x_field="x", y_fields=["y"], data=[{"x": index, "y": index} for index in range(101)], source_query_ids=["query_001"])


def test_chart_spec_rejects_unsupported_or_executable_configuration() -> None:
    with pytest.raises(ValidationError):
        ChartSpec(type="radar", title="No", data=[{"x": 1}], source_query_ids=["query_001"])  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        ChartSpec(type="line", title="No code", x_field="x", y_fields=["y"], data=[{"x": 1, "y": {"formatter": "alert(1)"}}], source_query_ids=["query_001"])


def test_a_single_observation_is_not_a_chart() -> None:
    # One point plots no trend and one bar ranks nothing; the number belongs in
    # the answer. The rejection names the alternative so the agent can recover.
    for chart_type in ("line", "area", "bar", "stacked_bar", "pie", "scatter"):
        with pytest.raises(ValidationError, match="not a chart"):
            ChartSpec(type=chart_type, title="One value", x_field="month", y_fields=["revenue"],  # type: ignore[arg-type]
                      data=[{"month": "2026-01", "revenue": 12}], source_query_ids=["query_001"])


def test_a_compact_grid_and_a_headline_metric_stay_available() -> None:
    # A one-row table is a legitimate detail grid, and a KPI card is the right
    # home for a single headline value. Neither is barred by the chart floor.
    table = ChartSpec(type="table", title="July detail", data=[{"month": "2026-07", "revenue": 12}],
                      source_query_ids=["query_001"])
    kpi = ChartSpec(type="kpi", title="Revenue", kpis=[{"label": "Revenue", "value": "$12M"}],
                    source_query_ids=["query_001"])

    assert table.type == "table"
    assert kpi.type == "kpi"
