"""Write the business metric reference to a file.

Run: python -m scripts.generate_metrics_doc [output_path]

The Workbench and the agent both read metric definitions from
``MetricRegistry`` at runtime; this renders the same definitions to a
human-readable page so a reader never has to open the source to know what a
metric means, what it requires, or whether it can be rerun.
"""

import sys
from pathlib import Path

DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "docs" / "METRICS.md"


def main() -> int:
    from app.analytics.semantics.metrics import MetricRegistry
    from app.analytics.semantics.metrics_doc import render_metrics_markdown

    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    markdown = render_metrics_markdown(MetricRegistry())
    output.write_text(markdown)
    print(f"Wrote {output} ({len(MetricRegistry().list_metrics())} metrics)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
