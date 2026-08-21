"""Validated, data-only analytical displays. Never contains executable frontend code."""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

ChartType = Literal["line", "bar", "stacked_bar", "area", "pie", "scatter", "table", "kpi"]


class ChartSeries(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str = Field(min_length=1, max_length=80)
    label: str | None = Field(default=None, max_length=120)


class KPIItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=80)
    change: str | None = Field(default=None, max_length=80)


class ChartFormatting(BaseModel):
    """Small, non-executable formatting vocabulary for the shared renderer."""

    model_config = ConfigDict(extra="forbid")
    currency: str | None = Field(default=None, max_length=12)
    decimal_places: int | None = Field(default=None, ge=0, le=4)
    show_legend: bool = True


class ChartSpec(BaseModel):
    """A bounded, declarative display produced from trusted query results."""
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid4()), max_length=80)
    type: ChartType
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    x_field: str | None = Field(default=None, max_length=80)
    y_fields: list[str] = Field(default_factory=list, max_length=8)
    series: list[ChartSeries] = Field(default_factory=list, max_length=8)
    data: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    source_query_ids: list[str] = Field(default_factory=list, min_length=1, max_length=12)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    kpis: list[KPIItem] = Field(default_factory=list, max_length=8)
    formatting: ChartFormatting = Field(default_factory=ChartFormatting)

    @model_validator(mode="after")
    def validate_data(self) -> "ChartSpec":
        if self.type == "kpi":
            if not self.kpis: raise ValueError("KPI displays require at least one KPI.")
            return self
        if not self.data: raise ValueError("Chart data cannot be empty.")
        fields = set().union(*(row.keys() for row in self.data))
        required = set(self.y_fields) | {series.field for series in self.series}
        if self.type != "table" and self.x_field: required.add(self.x_field)
        missing = required - fields
        if missing: raise ValueError(f"Chart fields are absent from data: {', '.join(sorted(missing))}")
        if self.type not in {"table", "pie", "kpi"} and not self.y_fields:
            raise ValueError("Charts require at least one y field.")
        if any(not isinstance(value, (str, int, float, bool, type(None))) for row in self.data for value in row.values()):
            raise ValueError("Chart data may contain only scalar values.")
        return self
