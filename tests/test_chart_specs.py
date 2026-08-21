import pytest
from pydantic import ValidationError

from app.analytics.charts import ChartSpec


def test_chart_spec_validates_bounded_data_and_fields() -> None:
    chart = ChartSpec(type="line", title="Monthly revenue", x_field="month", y_fields=["revenue"], data=[{"month": "2026-01", "revenue": 12}], source_query_ids=["query_001"])
    assert chart.type == "line"
    with pytest.raises(ValidationError, match="absent"):
        ChartSpec(type="bar", title="Bad", x_field="category", y_fields=["revenue"], data=[{"category": "A"}], source_query_ids=["query_001"])
    with pytest.raises(ValidationError):
        ChartSpec(type="line", title="Too many", x_field="x", y_fields=["y"], data=[{"x": index, "y": index} for index in range(101)], source_query_ids=["query_001"])


def test_chart_spec_rejects_unsupported_or_executable_configuration() -> None:
    with pytest.raises(ValidationError):
        ChartSpec(type="radar", title="No", data=[{"x": 1}], source_query_ids=["query_001"])  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        ChartSpec(type="line", title="No code", x_field="x", y_fields=["y"], data=[{"x": 1, "y": {"formatter": "alert(1)"}}], source_query_ids=["query_001"])
