"""What a reader may change about a report, expressed as data rather than SQL.

A rerun request names a metric, a period, dimensions and filters. It never
carries a SQL fragment, a column name or a value that becomes part of the
statement's text: every identifier the compiler emits comes from the metric
definition, and every value the reader supplies is bound as a parameter.

That split is the whole security model. These contracts exist to make the
request side of it inert.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: Time buckets a period may be grouped into. A closed set, because the grain
#: reaches the statement as a ``date_trunc`` literal.
Grain = Literal["day", "week", "month", "quarter", "year"]

#: Comparisons a filter may use. A closed set, because the operator reaches the
#: statement as text; the value beside it never does.
FilterOperator = Literal["eq", "ne", "in", "not_in", "gt", "gte", "lt", "lte"]

#: What a filter value may be. Structures are refused: a document compares
#: scalars, and anything richer would be a query the reader wrote.
FilterValue = str | int | float | bool

#: The furthest apart a period's ends may be, so one request cannot ask for a
#: scan of the whole table.
MAX_PERIOD_DAYS = 366 * 5


class ReportPeriod(BaseModel):
    """A half-open date range, ``start`` inclusive and ``end`` exclusive.

    Half-open because a closed range over timestamps either drops the last day's
    evening or double-counts a boundary, depending on how it is written, and
    both mistakes are invisible in a published total.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    start: date
    end: date

    @model_validator(mode="after")
    def validate_range(self) -> ReportPeriod:
        if self.end <= self.start:
            raise ValueError("A period must end after it starts.")
        if (self.end - self.start).days > MAX_PERIOD_DAYS:
            raise ValueError("A period may not span more than five years.")
        return self

    def describe(self) -> str:
        """The period as a reader sees it printed, with an inclusive last day."""

        from datetime import timedelta

        last = self.end - timedelta(days=1)
        if self.start == last:
            return self.start.isoformat()
        return f"{self.start.isoformat()} to {last.isoformat()}"


class MetricFilter(BaseModel):
    """One comparison against a field the metric declares as filterable."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field: str = Field(min_length=1, max_length=64)
    operator: FilterOperator = "eq"
    #: A single value, or the members for ``in``/``not_in``. Always bound.
    value: FilterValue | list[FilterValue] = Field(union_mode="left_to_right")

    @model_validator(mode="after")
    def validate_value_shape(self) -> MetricFilter:
        members = self.operator in {"in", "not_in"}
        if members and not isinstance(self.value, list):
            raise ValueError(f"The {self.operator} operator needs a list of values.")
        if not members and isinstance(self.value, list):
            raise ValueError(f"The {self.operator} operator needs a single value.")
        if isinstance(self.value, list):
            if not self.value:
                raise ValueError("A membership filter needs at least one value.")
            if len(self.value) > 50:
                raise ValueError("A membership filter may list at most 50 values.")
        return self


class MetricParameters(BaseModel):
    """Everything a reader may change about one factual section of a report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    metric: str = Field(min_length=1, max_length=64)
    period: ReportPeriod
    #: Dimension names the metric declares. Order is the reported column order.
    dimensions: list[str] = Field(default_factory=list, max_length=3)
    filters: list[MetricFilter] = Field(default_factory=list, max_length=8)
    #: The bucket a ``period`` dimension is grouped into. Ignored when the
    #: request does not group by period.
    grain: Grain = "month"

    @model_validator(mode="after")
    def validate_dimensions(self) -> MetricParameters:
        if len(set(self.dimensions)) != len(self.dimensions):
            raise ValueError("A dimension may be requested only once.")
        return self
