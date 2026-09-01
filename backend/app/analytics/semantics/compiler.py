"""Compile a metric request into one validated, parameterised statement.

The reader chooses a metric, a period, dimensions and filters. None of those
choices becomes SQL text: a dimension resolves to an expression the definition
declares, a filter resolves to a column the definition declares and an operator
from a closed set, and every value the reader supplied is bound.

That is the difference between this and rendering a template. There is no path
by which a request contributes a fragment, an identifier, a function or a second
statement — not because the input is scrubbed, but because it is never
concatenated in the first place. The compiled statement is then handed to the
same AST validator that guards the agent's own SQL, which is the last word on
whether it may run.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from app.analytics.semantics.metrics import MetricDefinition
from app.analytics.semantics.parameters import (
    FilterOperator,
    Grain,
    MetricFilter,
    MetricParameters,
)

#: SQL comparisons, by the operator name a request may use. The reader picks a
#: key; only the value is ever emitted.
_COMPARISONS: dict[FilterOperator, str] = {
    "eq": "=", "ne": "<>", "gt": ">", "gte": ">=", "lt": "<", "lte": "<=",
}
_MEMBERSHIP: dict[FilterOperator, str] = {"in": "IN", "not_in": "NOT IN"}

#: The name a period grouping is requested under, and the column it reports as.
PERIOD_DIMENSION = "period"

#: Guards a developer mistake rather than a reader's input: a declared
#: expression that is not a plain column reference or a bounded function call
#: would put something unreviewed into every statement using it.
_SAFE_EXPRESSION = re.compile(r"^[A-Za-z0-9_.,'() :\-]+$")


class MetricCompilationError(ValueError):
    """Raised when a request names something the metric does not declare."""


@dataclass(frozen=True, slots=True)
class CompiledMetricQuery:
    """One statement, its bound values, and what it will report."""

    metric: str
    sql: str
    parameters: dict[str, Any]
    #: Dimension aliases in reported order, then the metric's value columns.
    dimension_columns: tuple[str, ...] = ()
    value_columns: tuple[str, ...] = ()
    tables: tuple[str, ...] = ()

    @property
    def columns(self) -> tuple[str, ...]:
        return self.dimension_columns + self.value_columns

    @property
    def fingerprint(self) -> str:
        """A stable digest of the statement, so two runs can be compared.

        Over the SQL text only. Values are bound, so the same shape asked over a
        different period keeps the same fingerprint — which is what makes it
        useful for saying "the same question, asked again".
        """

        return hashlib.sha256(self.sql.encode("utf-8")).hexdigest()[:16]


def _period_expression(metric: MetricDefinition, grain: Grain) -> str:
    """Bucket the metric's own time column at a grain from the closed set.

    The expression is declared by the metric and carries a ``{grain}`` slot; the
    compiler substitutes a validated literal from ``Grain`` and nothing else.
    Guessing the table alias here instead would silently emit ``o.`` into a
    statement whose only table is aliased ``p``.
    """

    if grain not in metric.supported_grains:
        raise MetricCompilationError(
            f"{metric.display_name} cannot be grouped by {grain}."
        )
    spec = metric.dimension_specs.get(PERIOD_DIMENSION)
    if spec is None:
        raise MetricCompilationError(f"{metric.display_name} cannot be grouped by period.")
    return spec.expression.replace("{grain}", grain)


def _dimension_fragments(
    metric: MetricDefinition, parameters: MetricParameters
) -> tuple[list[str], list[str]]:
    """Return the select expressions and the aliases they report under."""

    selects: list[str] = []
    aliases: list[str] = []
    for name in parameters.dimensions:
        spec = metric.dimension_specs.get(name)
        if spec is None:
            available = ", ".join(sorted(metric.dimension_specs)) or "none"
            raise MetricCompilationError(
                f"{metric.display_name} cannot be grouped by {name!r}. Available: {available}."
            )
        alias = spec.alias
        expression = (_period_expression(metric, parameters.grain)
                      if name == PERIOD_DIMENSION else spec.expression)
        if not _SAFE_EXPRESSION.match(expression):
            raise MetricCompilationError(f"The {name} dimension is not a safe expression.")
        selects.append(f"{expression} AS {alias}")
        aliases.append(alias)
    return selects, aliases


def _filter_fragments(
    metric: MetricDefinition, filters: list[MetricFilter]
) -> tuple[list[str], dict[str, Any]]:
    """Return the predicates and the values they bind, never inlining a value."""

    predicates: list[str] = []
    bound: dict[str, Any] = {}
    for index, item in enumerate(filters):
        spec = metric.filter_specs.get(item.field)
        if spec is None:
            available = ", ".join(sorted(metric.filter_specs)) or "none"
            raise MetricCompilationError(
                f"{metric.display_name} cannot be filtered by {item.field!r}. Available: {available}."
            )
        if item.operator not in spec.operators:
            allowed = ", ".join(spec.operators)
            raise MetricCompilationError(
                f"The {item.field} filter does not support {item.operator!r}. Allowed: {allowed}."
            )
        if not _SAFE_EXPRESSION.match(spec.column):
            raise MetricCompilationError(f"The {item.field} filter is not a safe column.")
        _check_value_type(item, spec.value_type)

        if item.operator in _MEMBERSHIP:
            names = []
            for position, value in enumerate(item.value):  # type: ignore[arg-type]
                key = f"filter_{index}_{position}"
                bound[key] = value
                names.append(f":{key}")
            predicates.append(f"{spec.column} {_MEMBERSHIP[item.operator]} ({', '.join(names)})")
        else:
            key = f"filter_{index}"
            bound[key] = item.value
            predicates.append(f"{spec.column} {_COMPARISONS[item.operator]} :{key}")
    return predicates, bound


def _check_value_type(item: MetricFilter, expected: str) -> None:
    """Refuse a value the field cannot hold, before the database sees it."""

    values = item.value if isinstance(item.value, list) else [item.value]
    for value in values:
        if expected == "number" and isinstance(value, bool):
            raise MetricCompilationError(f"The {item.field} filter expects a number.")
        if expected == "number" and not isinstance(value, (int, float)):
            raise MetricCompilationError(f"The {item.field} filter expects a number.")
        if expected == "string" and not isinstance(value, str):
            raise MetricCompilationError(f"The {item.field} filter expects text.")
        if expected == "boolean" and not isinstance(value, bool):
            raise MetricCompilationError(f"The {item.field} filter expects true or false.")


def compile_metric(
    metric: MetricDefinition, parameters: MetricParameters
) -> CompiledMetricQuery:
    """Build the statement for one metric request.

    Raises ``MetricCompilationError`` when the request names a dimension, field
    or operator the metric does not declare — which is the only way a request
    can fail here, because nothing else about it reaches the statement.
    """

    if not metric.is_rerunnable or not metric.sql_template:
        raise MetricCompilationError(
            f"{metric.display_name} has no compiled definition and cannot be recomputed "
            "without an agent turn."
        )
    if metric.name != parameters.metric:
        raise MetricCompilationError("The request and the definition name different metrics.")

    selects, aliases = _dimension_fragments(metric, parameters)
    predicates, bound = _filter_fragments(metric, parameters.filters)

    dimensions = "".join(f"{select},\n       " for select in selects)
    filters = "".join(f"AND {predicate}\n  " for predicate in predicates).rstrip()
    positions = ", ".join(str(index + 1) for index in range(len(selects)))
    group_by = f"GROUP BY {positions}\nORDER BY {positions}" if selects else ""

    sql = (
        metric.sql_template
        .replace("{dimensions}", dimensions)
        .replace("{filters}", filters)
        .replace("{group_by}", group_by)
    )
    sql = "\n".join(line.rstrip() for line in sql.splitlines() if line.strip())

    return CompiledMetricQuery(
        metric=metric.name,
        sql=sql,
        parameters={
            "period_start": parameters.period.start,
            "period_end": parameters.period.end,
            **bound,
        },
        dimension_columns=tuple(aliases),
        value_columns=tuple(metric.value_columns),
        tables=tuple(metric.required_tables),
    )
