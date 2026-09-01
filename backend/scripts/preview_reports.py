"""Render sample reports and page images for visual inspection.

Run: python -m scripts.preview_reports [output_dir]

Automated checks read a generated document back and assert what it says. They
cannot see that a bullet glyph is a speck, that a figure heading has been left
stranded at the foot of a page, or that a dashboard's cards have collapsed into
a table — all of which happened during development and were caught only by
looking. This produces one PDF, one DOCX and a PNG of every page for each
template, from fixed sample data, so a layout change can be eyeballed.

The sample run is invented for layout purposes and is not evidence of anything;
nothing here goes near a real analysis.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "var" / ".runtime" / "previews"

GENERATED_AT = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]

ANSWER = (
    "## Revenue grew 18% year on year\n\n"
    "Electronics led the period at $163M, with the paid channel contributing most of "
    "the increase.\n\n"
    "- Electronics is the largest category by revenue.\n"
    "- Refund rate improved against the prior period.\n"
)

CAVEATS = [
    "August 2026 is a partial month, so the total understates the period.",
    "Refund timing may differ from order timing.",
]


def _charts():
    from app.analytics.presentation.charts import ChartSpec

    return [
        ChartSpec(
            id="kpi", type="kpi", title="Headlines", source_query_ids=["query_001"],
            kpis=[
                {"label": "Revenue", "value": "$163M", "change": "+18% YoY",
                 "raw_value": 163000000, "source_column": "revenue",
                 "row_selector": {"period": "2026-08"}},
                {"label": "Orders", "value": "12,400", "change": "+6% YoY",
                 "raw_value": 12400, "source_column": "orders",
                 "row_selector": {"period": "2026-08"}},
                {"label": "Avg order value", "value": "$131", "change": "+11% YoY",
                 "raw_value": 131.4, "source_column": "aov",
                 "row_selector": {"period": "2026-08"}},
                {"label": "Refund rate", "value": "2.4%", "change": "-0.3pp",
                 "raw_value": 2.4, "source_column": "refund_rate",
                 "row_selector": {"period": "2026-08"}},
            ],
        ),
        ChartSpec(
            id="trend", type="line", title="Revenue by month", x_field="month",
            y_fields=["revenue"], source_query_ids=["query_002"],
            data=[{"month": month, "revenue": 120 + index * 9}
                  for index, month in enumerate(MONTHS)],
        ),
        ChartSpec(
            id="bar", type="bar", title="Revenue by category", x_field="category",
            y_fields=["revenue"], source_query_ids=["query_003"],
            data=[{"category": name, "revenue": value} for name, value in
                  [("Electronics", 163), ("Fashion", 63), ("Home", 44), ("Sports", 31)]],
        ),
        ChartSpec(
            id="mix", type="stacked_bar", title="Channel mix", x_field="month",
            y_fields=["revenue"], source_query_ids=["query_005"],
            data=[{"month": month, "channel": channel,
                   "revenue": 40 + index * 3 + (7 if channel == "paid" else 0)}
                  for index, month in enumerate(MONTHS) for channel in ("paid", "organic")],
        ),
        ChartSpec(
            id="grid", type="table", title="Payment failures by method",
            source_query_ids=["query_004"],
            data=[{"method": method, "failures": failures, "share": share}
                  for method, failures, share in
                  [("Visa", 803, "41%"), ("Mastercard", 612, "31%"),
                   ("Amex", 91, "5%"), ("PayPal", 447, "23%")]],
        ),
    ]


def _sources():
    from app.contracts.answers import AnswerSource

    described = [
        ("query_001", "Headline revenue, orders, AOV and refund rate",
         ["orders", "refunds"], ["revenue", "orders", "aov", "refund_rate"], 1),
        ("query_002", "Monthly revenue trend", ["orders"], ["month", "revenue"], 6),
        ("query_003", "Revenue by product category",
         ["orders", "order_items", "product_categories"], ["category", "revenue"], 4),
        ("query_004", "Payment failures by method",
         ["payments", "payment_methods"], ["method", "failures", "share"], 4),
        ("query_005", "Revenue by channel and month",
         ["orders", "web_sessions"], ["month", "channel", "revenue"], 12),
    ]
    return [
        AnswerSource(id=query_id, run_id="run-preview", label=label, referenced_tables=tables,
                     columns=columns, row_count=rows,
                     executed_at=GENERATED_AT.replace(hour=9, minute=15 + index))
        for index, (query_id, label, tables, columns, rows) in enumerate(described)
    ]


def main() -> int:
    from app.analytics.presentation.compiler import compile_report
    from app.analytics.presentation.documents import write_docx, write_pdf
    from app.analytics.presentation.rasterize import render_chart_png
    from app.analytics.presentation.templates import ReportTemplateRegistry

    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    output.mkdir(parents=True, exist_ok=True)

    try:
        import pypdfium2
    except ImportError:
        pypdfium2 = None
        print("pypdfium2 is not installed; writing documents without page images.")

    charts = _charts()
    drawn = {chart.id: chart for chart in charts}
    sources = _sources()

    for template in ReportTemplateRegistry().list_templates():
        report = compile_report(
            template=template, run_id="run-preview", answer=ANSWER, charts=charts,
            sources=sources, generated_at=GENERATED_AT, period="August 2026",
            caveats=CAVEATS, report_id=f"preview-{template.name}",
        )
        images = {
            block.chart_id: rendered
            for block in report.blocks_of("chart")
            if (rendered := render_chart_png(
                drawn[block.chart_id], output / f"{template.name}-{block.chart_id}.png",
                palette=template.theme.chart_palette,
            ))
        }
        pdf = write_pdf(report, images, output / f"{template.name}.pdf", template.theme)
        write_docx(report, images, output / f"{template.name}.docx", template.theme)

        pages = 0
        if pypdfium2 is not None:
            document = pypdfium2.PdfDocument(str(pdf))
            pages = len(document)
            for index in range(pages):
                document[index].render(scale=1.4).to_pil().save(
                    output / f"{template.name}-p{index + 1}.png"
                )
        print(f"{template.name:26} {template.orientation:9} {pages} page(s)")

    print(f"\nWrote previews to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
