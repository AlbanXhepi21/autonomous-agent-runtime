"""What the model may state as a limitation, and what survives to a report.

A finish action arrives after the analysis is finished. Rejecting it over a
caveat that ran long or was repeated would throw that work away, so the bounds
are enforced by normalizing rather than by raising — and everything downstream
can then assume it holds a list a report may print.
"""

import pytest

from app.contracts.actions import (
    MAX_CAVEAT_LENGTH,
    MAX_CAVEATS,
    AgentAction,
    normalize_caveats,
)
from app.runtime.state import AgentState
from tests.support import ScriptedLLM, make_runner


def _finish(caveats: object) -> AgentAction:
    return AgentAction(action_type="finish", reasoning_summary="Done.",
                       final_answer="Revenue grew 18%.", caveats=caveats)


def test_a_finish_action_states_no_limitations_by_default() -> None:
    """Older callers and older runs both read as having stated none."""

    action = AgentAction(action_type="finish", reasoning_summary="Done.",
                         final_answer="Revenue grew 18%.")

    assert action.caveats == []


def test_stated_limitations_are_kept_in_the_order_written() -> None:
    action = _finish([
        "Refund timing may differ from order timing.",
        "August 2026 is a partial month.",
    ])

    assert action.caveats == [
        "Refund timing may differ from order timing.",
        "August 2026 is a partial month.",
    ]


def test_surrounding_whitespace_is_removed() -> None:
    assert _finish(["  Sample of 12 orders.\n"]).caveats == ["Sample of 12 orders."]


def test_blank_entries_are_dropped_rather_than_published() -> None:
    action = _finish(["", "   ", "\n\t", "Sample of 12 orders."])

    assert action.caveats == ["Sample of 12 orders."]


def test_more_than_the_maximum_is_truncated_to_the_maximum() -> None:
    action = _finish([f"Limitation {index}." for index in range(MAX_CAVEATS + 5)])

    assert len(action.caveats) == MAX_CAVEATS
    assert action.caveats[0] == "Limitation 0."
    assert action.caveats[-1] == f"Limitation {MAX_CAVEATS - 1}."


def test_an_over_long_caveat_is_omitted_rather_than_cut_mid_sentence() -> None:
    """A truncated sentence would publish a misleading fragment."""

    at_limit = "x" * MAX_CAVEAT_LENGTH
    over_limit = "y" * (MAX_CAVEAT_LENGTH + 1)

    action = _finish([at_limit, over_limit, "Sample of 12 orders."])

    assert action.caveats == [at_limit, "Sample of 12 orders."]


def test_repeated_limitations_are_stated_once() -> None:
    """Duplicates that differ only in case or spacing are the same limitation."""

    action = _finish([
        "Sample of 12 orders.",
        "Sample of 12 orders.",
        "  sample   of 12 ORDERS.  ",
        "Refund timing may differ.",
    ])

    assert action.caveats == ["Sample of 12 orders.", "Refund timing may differ."]


def test_duplicates_do_not_consume_the_budget() -> None:
    action = _finish(["Repeated."] * 20 + ["Distinct."])

    assert action.caveats == ["Repeated.", "Distinct."]


@pytest.mark.parametrize("value", [None, "a string", 42, {"a": 1}])
def test_anything_that_is_not_a_list_states_no_limitations(value: object) -> None:
    assert normalize_caveats(value) == []


def test_non_string_entries_are_ignored() -> None:
    assert _finish(["Real limitation.", 7, None, ["nested"]]).caveats == ["Real limitation."]


def test_normalizing_an_already_normalized_list_changes_nothing() -> None:
    """Publishing re-normalizes what it loaded, so this has to be idempotent."""

    once = normalize_caveats(["  Repeated.  ", "Repeated.", "Distinct."])

    assert normalize_caveats(once) == once


def test_markup_is_carried_as_text_and_never_as_structure() -> None:
    """A caveat is prose; nothing downstream may treat it as markup."""

    hostile = "<script>alert(1)</script> Sample too small."

    action = _finish([hostile])

    # Stored verbatim as a string. The DOCX writer sets it as a run of text and
    # the PDF writer escapes it; neither interprets it as an element.
    assert action.caveats == [hostile]
    assert isinstance(action.caveats[0], str)


@pytest.mark.parametrize(
    "action_type,payload",
    [
        ("use_tool", {"tool_name": "calculator"}),
        ("load_skill", {"skill_name": "data_analysis"}),
    ],
)
def test_only_a_finish_action_may_carry_limitations(action_type: str, payload: dict) -> None:
    with pytest.raises(ValueError, match="only finish actions may carry caveats"):
        AgentAction(action_type=action_type, reasoning_summary="x",  # type: ignore[arg-type]
                    caveats=["Sample of 12 orders."], **payload)


@pytest.mark.asyncio
async def test_the_runtime_records_what_the_model_stated() -> None:
    runner = make_runner(ScriptedLLM(_finish(["Sample of 12 orders.", "Sample of 12 orders."])))

    result = await runner.run("Investigate refunds", state=AgentState(goal="Investigate refunds"))

    assert result.completed
    assert result.answer_caveats == ["Sample of 12 orders."]


@pytest.mark.asyncio
async def test_a_run_that_stated_nothing_reports_an_empty_list() -> None:
    runner = make_runner(ScriptedLLM(
        AgentAction(action_type="finish", reasoning_summary="Done.", final_answer="No limits.")
    ))

    result = await runner.run("Investigate refunds", state=AgentState(goal="Investigate refunds"))

    assert result.answer_caveats == []
