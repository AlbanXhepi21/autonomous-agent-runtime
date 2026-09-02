"""The metric reference is generated from the registry, never hand-typed.

If a metric definition changes and the checked-in doc is not regenerated, a
reader keeps reading a description that disagrees with what the compiler
actually runs. Regenerate with `python -m scripts.generate_metrics_doc` from
backend/.
"""

from app.analytics.semantics.metrics import MetricRegistry
from app.analytics.semantics.metrics_doc import render_metrics_markdown
from tests.support import REPO_ROOT

DOC = REPO_ROOT / "docs" / "METRICS.md"


def test_committed_metrics_doc_matches_the_registry() -> None:
    if not DOC.exists():
        import pytest

        pytest.fail(f"{DOC} is missing; run `python -m scripts.generate_metrics_doc` from backend/.")

    current = render_metrics_markdown(MetricRegistry())
    committed = DOC.read_text()

    assert committed == current, (
        "A metric definition changed but docs/METRICS.md was not regenerated. "
        "Run `python -m scripts.generate_metrics_doc` from backend/ and commit the result."
    )
