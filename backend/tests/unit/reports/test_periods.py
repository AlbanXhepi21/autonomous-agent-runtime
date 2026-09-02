"""Resolving a saved report's relative period into an exact, half-open window.

Every case here pins ``today`` explicitly rather than reading the clock, so a
month/quarter/year boundary is exercised deterministically instead of only
when the calendar happens to land on one.
"""

from datetime import date

import pytest

from app.reports.contracts import RelativePeriod
from app.reports.periods import RelativePeriodResolutionError, resolve_relative_period


def test_current_month_runs_from_the_first_through_today_exclusive() -> None:
    resolved = resolve_relative_period(RelativePeriod(kind="current_month"), today=date(2026, 1, 15))

    assert resolved.period.start == date(2026, 1, 1)
    assert resolved.period.end == date(2026, 2, 1)


def test_previous_month_at_the_start_of_a_year_crosses_into_last_december() -> None:
    resolved = resolve_relative_period(RelativePeriod(kind="previous_month"), today=date(2026, 1, 15))

    assert resolved.period.start == date(2025, 12, 1)
    assert resolved.period.end == date(2026, 1, 1)


def test_previous_month_on_the_first_of_the_month_still_means_the_prior_month() -> None:
    resolved = resolve_relative_period(RelativePeriod(kind="previous_month"), today=date(2026, 3, 1))

    assert resolved.period.start == date(2026, 2, 1)
    assert resolved.period.end == date(2026, 3, 1)


def test_current_quarter_anchors_to_the_quarters_first_month() -> None:
    resolved = resolve_relative_period(RelativePeriod(kind="current_quarter"), today=date(2026, 4, 1))

    assert resolved.period.start == date(2026, 4, 1)
    assert resolved.period.end == date(2026, 7, 1)


@pytest.mark.parametrize(
    "today, expected_start, expected_end",
    [
        (date(2026, 2, 14), date(2026, 1, 1), date(2026, 4, 1)),
        (date(2026, 5, 1), date(2026, 4, 1), date(2026, 7, 1)),
        (date(2026, 8, 31), date(2026, 7, 1), date(2026, 10, 1)),
        (date(2026, 11, 3), date(2026, 10, 1), date(2027, 1, 1)),
    ],
)
def test_current_quarter_covers_every_calendar_quarter(
    today: date, expected_start: date, expected_end: date,
) -> None:
    resolved = resolve_relative_period(RelativePeriod(kind="current_quarter"), today=today)

    assert (resolved.period.start, resolved.period.end) == (expected_start, expected_end)


def test_previous_quarter_at_the_start_of_a_year_crosses_into_last_years_q4() -> None:
    resolved = resolve_relative_period(RelativePeriod(kind="previous_quarter"), today=date(2026, 1, 1))

    assert resolved.period.start == date(2025, 10, 1)
    assert resolved.period.end == date(2026, 1, 1)


def test_current_year_runs_from_january_first_through_next_january_first() -> None:
    resolved = resolve_relative_period(RelativePeriod(kind="current_year"), today=date(2026, 6, 30))

    assert resolved.period.start == date(2026, 1, 1)
    assert resolved.period.end == date(2027, 1, 1)


def test_previous_year_at_the_start_of_a_year_is_the_full_prior_year() -> None:
    resolved = resolve_relative_period(RelativePeriod(kind="previous_year"), today=date(2026, 1, 1))

    assert resolved.period.start == date(2025, 1, 1)
    assert resolved.period.end == date(2026, 1, 1)


def test_last_n_days_excludes_today_itself_as_incomplete() -> None:
    resolved = resolve_relative_period(RelativePeriod(kind="last_n_days", days=7), today=date(2026, 1, 3))

    # Today is never a complete day, so the window ends at today (exclusive)
    # and reaches back exactly 7 days, crossing into the prior December.
    assert resolved.period.start == date(2025, 12, 27)
    assert resolved.period.end == date(2026, 1, 3)


def test_fixed_ignores_today_entirely() -> None:
    fixed = RelativePeriod(kind="fixed", start=date(2020, 1, 1), end=date(2020, 4, 1))

    resolved = resolve_relative_period(fixed, today=date(2026, 9, 1))

    assert resolved.period.start == date(2020, 1, 1)
    assert resolved.period.end == date(2020, 4, 1)


def test_every_resolution_names_the_rule_and_the_reference_date() -> None:
    resolved = resolve_relative_period(RelativePeriod(kind="current_month"), today=date(2026, 1, 15))

    assert "current calendar month" in resolved.description
    assert "2026-01-15" in resolved.description


def test_an_unknown_kind_is_impossible_to_construct() -> None:
    # RelativePeriod's own Literal type already forbids this at the Pydantic
    # layer; the resolver's fallback branch exists only as a defensive guard.
    with pytest.raises(ValueError):
        RelativePeriod(kind="recently")  # type: ignore[arg-type]


def test_resolve_relative_period_error_is_a_value_error() -> None:
    assert issubclass(RelativePeriodResolutionError, ValueError)
