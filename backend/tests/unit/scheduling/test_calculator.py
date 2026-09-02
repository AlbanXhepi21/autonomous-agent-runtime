"""Computing a schedule's next run instant: every kind, and its boundaries."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from app.scheduling.calculator import compute_next_run
from app.scheduling.contracts import ScheduleConfig


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


def test_daily_fires_at_the_configured_time() -> None:
    config = ScheduleConfig(kind="daily", hour=6, minute=0)

    assert compute_next_run(config, tz_name="UTC", after=_utc(2026, 1, 15, 5, 0)) == _utc(2026, 1, 15, 6, 0)


def test_daily_after_todays_run_rolls_to_tomorrow() -> None:
    config = ScheduleConfig(kind="daily", hour=6, minute=0)

    assert compute_next_run(config, tz_name="UTC", after=_utc(2026, 1, 15, 7, 0)) == _utc(2026, 1, 16, 6, 0)


def test_weekly_finds_the_next_matching_weekday() -> None:
    # 2026-01-15 is a Thursday (weekday 3); Monday is weekday 0.
    config = ScheduleConfig(kind="weekly", day_of_week=0, hour=9, minute=0)

    result = compute_next_run(config, tz_name="UTC", after=_utc(2026, 1, 15, 12, 0))

    assert result == _utc(2026, 1, 19, 9, 0)
    assert result.astimezone(UTC).weekday() == 0


def test_weekly_on_the_matching_day_but_before_the_time_fires_today() -> None:
    # 2026-01-19 is a Monday.
    config = ScheduleConfig(kind="weekly", day_of_week=0, hour=9, minute=0)

    assert compute_next_run(config, tz_name="UTC", after=_utc(2026, 1, 19, 8, 0)) == _utc(2026, 1, 19, 9, 0)


def test_monthly_day_28_lands_correctly_in_a_short_february() -> None:
    config = ScheduleConfig(kind="monthly", day_of_month=28, hour=0, minute=0)

    # 2026 is not a leap year -- February has 28 days.
    assert compute_next_run(config, tz_name="UTC", after=_utc(2026, 1, 29, 0, 0)) == _utc(2026, 2, 28, 0, 0)


def test_monthly_crosses_a_year_boundary() -> None:
    config = ScheduleConfig(kind="monthly", day_of_month=15, hour=0, minute=0)

    assert compute_next_run(config, tz_name="UTC", after=_utc(2026, 12, 20, 0, 0)) == _utc(2027, 1, 15, 0, 0)


def test_monthly_day_28_still_fires_correctly_in_a_leap_february() -> None:
    config = ScheduleConfig(kind="monthly", day_of_month=28, hour=0, minute=0)

    # 2028 is a leap year -- day 28 exists in February regardless.
    assert compute_next_run(config, tz_name="UTC", after=_utc(2028, 1, 29, 0, 0)) == _utc(2028, 2, 28, 0, 0)


@pytest.mark.parametrize(
    "after, expected",
    [
        (_utc(2026, 2, 14, 0, 0), _utc(2026, 4, 15, 8, 0)),
        (_utc(2026, 5, 1, 0, 0), _utc(2026, 7, 15, 8, 0)),
        (_utc(2026, 8, 31, 0, 0), _utc(2026, 10, 15, 8, 0)),
        (_utc(2026, 11, 1, 0, 0), _utc(2027, 1, 15, 8, 0)),
    ],
)
def test_quarterly_covers_every_calendar_quarter(after: datetime, expected: datetime) -> None:
    config = ScheduleConfig(kind="quarterly", month_of_quarter=1, day_of_month=15, hour=8, minute=0)

    assert compute_next_run(config, tz_name="UTC", after=after) == expected


def test_quarterly_month_of_quarter_selects_the_right_month_each_cycle() -> None:
    # month_of_quarter=2 -> Feb/May/Aug/Nov.
    config = ScheduleConfig(kind="quarterly", month_of_quarter=2, day_of_month=1, hour=0, minute=0)

    assert compute_next_run(config, tz_name="UTC", after=_utc(2026, 1, 1, 0, 0)) == _utc(2026, 2, 1, 0, 0)
    assert compute_next_run(config, tz_name="UTC", after=_utc(2026, 2, 2, 0, 0)) == _utc(2026, 5, 1, 0, 0)


def test_fixed_time_of_day_is_honored_regardless_of_kind() -> None:
    config = ScheduleConfig(kind="daily", hour=23, minute=45)

    assert compute_next_run(config, tz_name="UTC", after=_utc(2026, 1, 1, 23, 44)) == _utc(2026, 1, 1, 23, 45)


# -- Timezone and DST boundaries -----------------------------------------------


def test_a_non_utc_timezone_converts_correctly_outside_dst() -> None:
    config = ScheduleConfig(kind="daily", hour=9, minute=0)

    # February: America/New_York is on EST (UTC-5).
    result = compute_next_run(config, tz_name="America/New_York", after=_utc(2026, 2, 1, 0, 0))

    assert result == _utc(2026, 2, 1, 14, 0)


def test_a_non_utc_timezone_converts_correctly_inside_dst() -> None:
    config = ScheduleConfig(kind="daily", hour=9, minute=0)

    # July: America/New_York is on EDT (UTC-4).
    result = compute_next_run(config, tz_name="America/New_York", after=_utc(2026, 7, 1, 0, 0))

    assert result == _utc(2026, 7, 1, 13, 0)


def test_the_utc_offset_shifts_across_a_spring_forward_transition() -> None:
    config = ScheduleConfig(kind="daily", hour=9, minute=0)

    # 2026-03-08 is the US spring-forward Sunday (2am -> 3am, EST -> EDT).
    before = compute_next_run(config, tz_name="America/New_York", after=_utc(2026, 3, 7, 20, 0))
    after = compute_next_run(config, tz_name="America/New_York", after=_utc(2026, 3, 8, 20, 0))

    assert before == _utc(2026, 3, 8, 13, 0)  # 9am already EDT on the transition day itself
    assert after == _utc(2026, 3, 9, 13, 0)  # and stays EDT the day after


def test_the_utc_offset_shifts_across_a_fall_back_transition() -> None:
    config = ScheduleConfig(kind="daily", hour=9, minute=0)

    # 2026-11-01 is the US fall-back Sunday.
    before = compute_next_run(config, tz_name="America/New_York", after=_utc(2026, 10, 31, 20, 0))
    after = compute_next_run(config, tz_name="America/New_York", after=_utc(2026, 11, 1, 20, 0))

    assert before == _utc(2026, 11, 1, 14, 0)
    assert after == _utc(2026, 11, 2, 14, 0)


def test_after_may_be_given_in_a_different_timezone_than_the_schedule() -> None:
    """'after' is always interpreted relative to the schedule's own clock."""

    config = ScheduleConfig(kind="daily", hour=6, minute=0)
    tokyo_after = datetime(2026, 1, 15, 20, 0, tzinfo=UTC).astimezone(ZoneInfo("Asia/Tokyo"))

    result = compute_next_run(config, tz_name="UTC", after=tokyo_after)

    assert result == _utc(2026, 1, 16, 6, 0)
