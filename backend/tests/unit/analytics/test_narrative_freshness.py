"""What happens to the prose when the figures beside it are recomputed.

The failure this prevents is quiet: a reader changes the period, the numbers
update, and a paragraph written about March is still sitting above them reading
as though it describes the new data. There is deliberately no state in which
that happens — the prose is either current, kept under a warning, or left out.

Rewriting it to match would need a model, and publishing never calls one.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from docx import Document
from pypdf import PdfReader

from app.analytics.presentation.compiler import compile_report, narrative_warning
from app.analytics.presentation.documents import write_docx, write_pdf
from app.analytics.presentation.templates import ReportTemplateRegistry
from app.contracts.answers import AnswerSource

ANSWER = "## Finding\nRevenue grew 18% in March.\n\n- Electronics led."
ORIGINAL = "March 2026"
REFRESHED = "2026-01-01 to 2026-03-31"


def _source() -> AnswerSource:
    return AnswerSource(id="rerun_001", kind="metric_rerun", run_id="run-1",
                        label="Revenue", metric="revenue", referenced_tables=["orders"])


def _report(status, period=REFRESHED, analysis_period=ORIGINAL):
    return compile_report(
        template=ReportTemplateRegistry().get("monthly_business_review"), run_id="run-1",
        answer=ANSWER, charts=[], sources=[_source()],
        generated_at=datetime(2026, 8, 31, tzinfo=timezone.utc),
        period=period, analysis_period=analysis_period, narrative_status=status,
    )


def _pdf_text(path: Path) -> str:
    return " ".join("\n".join(page.extract_text() for page in PdfReader(str(path)).pages).split())


def _docx_text(path: Path) -> str:
    return " ".join(" ".join(p.text for p in Document(str(path)).paragraphs).split())


def test_an_unchanged_report_needs_no_warning() -> None:
    report = _report("current", period=ORIGINAL, analysis_period=ORIGINAL)

    assert report.narrative_period_status == "current"
    assert report.narrative_warning is None
    assert report.blocks_of("narrative")[0].lines, "the prose is printed as written"
    assert report.blocks_of("narrative")[0].warning is None


def test_pinned_prose_keeps_its_words_and_gains_a_warning() -> None:
    report = _report("pinned_to_original_period")

    block = report.blocks_of("narrative")[0]
    assert block.lines, "the prose is kept verbatim"
    assert "Revenue grew 18% in March." in [line.text for line in block.lines]
    assert block.warning is not None
    assert ORIGINAL in block.warning and REFRESHED in block.warning
    assert report.narrative_period_status == "pinned_to_original_period"


def test_excluded_prose_is_left_out_and_says_why() -> None:
    report = _report("excluded_from_refreshed_report")

    block = report.blocks_of("narrative")[0]
    assert block.lines == []
    assert "recomputed for a different period" in block.empty_message
    # And the words themselves are nowhere in the document.
    assert "Revenue grew 18%" not in report.model_dump_json()


def test_the_two_periods_are_both_recorded() -> None:
    """A reader can see what the prose was for and what the figures are for."""

    report = _report("pinned_to_original_period")

    assert report.analysis_period == ORIGINAL
    assert report.displayed_period == REFRESHED


def test_the_warning_names_both_periods() -> None:
    warning = narrative_warning("pinned_to_original_period", "March 2026", "April 2026")

    assert warning is not None
    assert "March 2026" in warning and "April 2026" in warning
    assert "does not describe them" in warning


@pytest.mark.parametrize("status", ["current", "excluded_from_refreshed_report"])
def test_no_warning_is_produced_where_none_is_needed(status: str) -> None:
    assert narrative_warning(status, "March 2026", "April 2026") is None  # type: ignore[arg-type]


@pytest.mark.parametrize("writer,read", [(write_pdf, _pdf_text), (write_docx, _docx_text)])
def test_both_formats_print_the_warning(writer, read, tmp_path: Path) -> None:
    """A warning only one format shows is worse than no warning at all."""

    path = writer(_report("pinned_to_original_period"), {}, tmp_path / "report.out")

    text = read(path)
    assert "Revenue grew 18% in March." in text, "the prose is still there"
    assert "has been kept unchanged" in text
    assert "does not describe them" in text


@pytest.mark.parametrize("writer,read", [(write_pdf, _pdf_text), (write_docx, _docx_text)])
def test_neither_format_prints_excluded_prose(writer, read, tmp_path: Path) -> None:
    path = writer(_report("excluded_from_refreshed_report"), {}, tmp_path / "report.out")

    text = read(path)
    assert "Revenue grew 18%" not in text
    assert "recomputed for a different period" in text


def test_there_is_no_state_that_reuses_prose_silently() -> None:
    """The vocabulary itself is what rules the quiet failure out."""

    from typing import get_args

    from app.analytics.presentation.document_model import NarrativeStatus

    assert set(get_args(NarrativeStatus)) == {
        "current", "pinned_to_original_period", "excluded_from_refreshed_report",
    }
    # Every state that is not `current` either warns or omits.
    for status in get_args(NarrativeStatus):
        report = _report(status)
        block = report.blocks_of("narrative")[0]
        if status == "current":
            continue
        assert block.warning is not None or not block.lines, status
