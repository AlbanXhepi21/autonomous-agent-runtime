"""Draw a validated ChartSpec as a PNG for documents that cannot run a browser.

The Workbench renders these specs with Recharts in the reader's browser, which
produces nothing a PDF or DOCX can embed. Rather than run a headless browser,
the same data-only spec is drawn again here with Matplotlib. The two renderers
will never be pixel-identical; they are deliberately given the same palette and
the same series rules so an exported chart reads as the same chart.

Matplotlib's pyplot keeps global figure state and is not safe to use from a web
worker, so the object API is used directly and every figure is closed.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from app.analytics.presentation.charts import ChartSpec

#: Shared with the Workbench renderer so a series keeps its colour on export.
COLORS = ("#176b87", "#3c9a79", "#d1873b", "#8064b5", "#cc5b63")

#: Types drawn as an image. Tables and KPI cards become document text instead.
RASTERIZABLE = frozenset({"line", "area", "bar", "stacked_bar", "pie", "scatter"})

_MAX_PIVOT_CATEGORIES = 8


def _series_label(chart: ChartSpec, field: str, index: int) -> str:
    for series in chart.series:
        if series.field == field and series.label:
            return series.label
    return field or f"Series {index + 1}"


def _pivot(chart: ChartSpec) -> tuple[list[Any], list[tuple[str, list[float | None]]]] | None:
    """Spread a long-form category column into one series per category.

    Mirrors ``prepareChart`` in the Workbench renderer. Kept in step with it by
    hand; the two exist because the export cannot reuse the browser's code.
    """

    if not chart.x_field or len(chart.y_fields) != 1 or chart.type not in {"line", "area", "bar", "stacked_bar"}:
        return None
    value_field = chart.y_fields[0]
    candidates = [key for key in (chart.data[0] or {}) if key not in {chart.x_field, value_field}]
    x_values = list(dict.fromkeys(row.get(chart.x_field) for row in chart.data))
    category_field = next(
        (
            field
            for field in candidates
            if 2 <= len({row[field] for row in chart.data if isinstance(row.get(field), str)}) <= _MAX_PIVOT_CATEGORIES
            and len(chart.data) > len(x_values)
        ),
        None,
    )
    if category_field is None:
        return None
    categories = list(dict.fromkeys(
        row[category_field] for row in chart.data if isinstance(row.get(category_field), str)
    ))
    lookup = {(row.get(chart.x_field), row.get(category_field)): row.get(value_field) for row in chart.data}
    return x_values, [
        (category, [_number(lookup.get((x, category))) for x in x_values]) for category in categories
    ]


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _plain(chart: ChartSpec) -> tuple[list[Any], list[tuple[str, list[float | None]]]]:
    x_values = [row.get(chart.x_field) for row in chart.data] if chart.x_field else list(range(len(chart.data)))
    return x_values, [
        (_series_label(chart, field, index), [_number(row.get(field)) for row in chart.data])
        for index, field in enumerate(chart.y_fields)
    ]


def render_chart_png(chart: ChartSpec, path: Path, *,
                     palette: Sequence[str] | None = None) -> Path | None:
    """Write one chart image, or return None for a type that is not a picture.

    The palette comes from the report's theme so an exported figure is set in
    the same colours as the document around it; without one, the shared default
    keeps a chart matching the Workbench.
    """

    if chart.type not in RASTERIZABLE or not chart.data:
        return None
    colors = tuple(palette) if palette else COLORS
    figure = Figure(figsize=(8, 4), dpi=144)
    FigureCanvasAgg(figure)
    axes = figure.add_subplot(111)
    try:
        if chart.type == "pie":
            _draw_pie(chart, axes, colors)
        elif chart.type == "scatter":
            _draw_scatter(chart, axes, colors)
        else:
            _draw_series(chart, axes, colors)
        axes.set_title(chart.title, fontsize=11, loc="left")
        axes.spines["top"].set_visible(False)
        axes.spines["right"].set_visible(False)
        figure.tight_layout()
        path.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(path, format="png")
    finally:
        figure.clear()
    return path


def _draw_series(chart: ChartSpec, axes: Any, palette: Sequence[str]) -> None:
    x_values, series = _pivot(chart) or _plain(chart)
    labels = [str(value) for value in x_values]
    positions = range(len(labels))
    stacked = chart.type == "stacked_bar"
    running = [0.0] * len(labels)
    width = 0.8 / max(len(series), 1)
    for index, (label, values) in enumerate(series):
        color = palette[index % len(palette)]
        heights = [value or 0.0 for value in values]
        if chart.type == "line":
            axes.plot(positions, [v if v is not None else float("nan") for v in values],
                      label=label, color=color, marker="o", markersize=3, linewidth=1.8)
        elif chart.type == "area":
            axes.fill_between(list(positions), running, [base + value for base, value in zip(running, heights, strict=True)],
                              label=label, color=color, alpha=0.55)
            running = [base + value for base, value in zip(running, heights, strict=True)]
        elif stacked:
            axes.bar(list(positions), heights, bottom=running, label=label, color=color, width=0.62)
            running = [base + value for base, value in zip(running, heights, strict=True)]
        else:
            offset = (index - (len(series) - 1) / 2) * width
            axes.bar([position + offset for position in positions], heights, label=label, color=color, width=width)
    axes.set_xticks(list(positions))
    longest = max((len(text) for text in labels), default=0)
    axes.set_xticklabels(labels, rotation=45 if longest > 6 else 0,
                         ha="right" if longest > 6 else "center", fontsize=8)
    axes.tick_params(axis="y", labelsize=8)
    axes.grid(axis="y", color="#e6eaf0", linewidth=0.8)
    axes.set_axisbelow(True)
    if len(series) > 1 and chart.formatting.show_legend:
        axes.legend(fontsize=8, frameon=False)


def _draw_pie(chart: ChartSpec, axes: Any, palette: Sequence[str]) -> None:
    value_field = chart.y_fields[0] if chart.y_fields else None
    if value_field is None:
        numeric = [key for key, value in chart.data[0].items() if isinstance(value, (int, float))]
        value_field = numeric[0] if numeric else None
    if value_field is None:
        return
    values = [abs(_number(row.get(value_field)) or 0.0) for row in chart.data]
    labels = [str(row.get(chart.x_field, "")) if chart.x_field else "" for row in chart.data]
    axes.pie(values, labels=labels, colors=[palette[index % len(palette)] for index in range(len(values))],
             autopct="%1.0f%%", textprops={"fontsize": 8})
    axes.axis("equal")


def _draw_scatter(chart: ChartSpec, axes: Any, palette: Sequence[str]) -> None:
    for index, field in enumerate(chart.y_fields):
        axes.scatter([_number(row.get(chart.x_field)) if chart.x_field else None for row in chart.data],
                     [_number(row.get(field)) for row in chart.data],
                     label=_series_label(chart, field, index), color=palette[index % len(palette)], s=18)
    axes.set_xlabel(chart.x_field or "", fontsize=8)
    axes.tick_params(labelsize=8)
    axes.grid(color="#e6eaf0", linewidth=0.8)
    axes.set_axisbelow(True)
    if len(chart.y_fields) > 1 and chart.formatting.show_legend:
        axes.legend(fontsize=8, frameon=False)
