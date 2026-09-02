"""Compute a schedule's next run instant, deterministically.

Every rule here works in the schedule's own local timezone -- a "6am daily"
schedule means 6am wall-clock time in that timezone, not 6am UTC -- and
returns an exact UTC instant, converted once at the end. That conversion is
where a daylight-saving transition is actually handled: ``zoneinfo`` resolves
a local wall-clock time to the correct UTC offset for that specific date, so
the same "9am America/New_York" schedule correctly becomes 13:00 UTC in
January (EST) and 13:00 UTC in July is wrong -- it becomes 13:00 UTC only in
winter; in summer (EDT, UTC-4) it becomes 13:00 UTC too only by coincidence of
this example -- what matters is that the local hour never drifts across a
transition, only its UTC offset does.

One documented limitation: a schedule whose wall-clock time falls inside a
"spring forward" gap (a local time that never occurs, e.g. 2:30am on the day
clocks jump from 2:00 to 3:00) is resolved by Python's ``zoneinfo`` using its
default fold behavior rather than snapped to the nearest valid instant. This
is rare (it only affects schedules deliberately set in the 0-1 hour range
that a specific timezone skips on a specific day of the year) and is called
out here rather than solved with a bespoke gap-detection algorithm.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from app.scheduling.contracts import ScheduleConfig

_WEEK_DAYS = 7


def _add_months(anchor: date, months: int) -> date:
    """The first of the month ``months`` away from ``anchor``'s month."""

    zero_based = anchor.month - 1 + months
    year = anchor.year + zero_based // 12
    month = zero_based % 12 + 1
    return date(year, month, 1)


def _quarter_cycle_month(month_of_quarter: int, anchor_month: int) -> bool:
    """Whether ``anchor_month`` is the Nth month of its calendar quarter."""

    return ((anchor_month - 1) % 3) + 1 == month_of_quarter


def _candidate_dates(config: ScheduleConfig, local_today: date):
    """Yield candidate local dates this schedule could fire on, nearest first.

    Only ever consulted for a handful of candidates before one is accepted,
    so a generator that walks forward one unit at a time is simpler than a
    closed-form formula for every kind and no slower in practice.
    """

    if config.kind == "daily":
        offset = 0
        while True:
            yield local_today + timedelta(days=offset)
            offset += 1

    elif config.kind == "weekly":
        assert config.day_of_week is not None
        offset = 0
        while True:
            candidate = local_today + timedelta(days=offset)
            if candidate.weekday() == config.day_of_week:
                yield candidate
            offset += 1

    elif config.kind == "monthly":
        assert config.day_of_month is not None
        month_start = date(local_today.year, local_today.month, 1)
        while True:
            yield date(month_start.year, month_start.month, config.day_of_month)
            month_start = _add_months(month_start, 1)

    elif config.kind == "quarterly":
        assert config.day_of_month is not None and config.month_of_quarter is not None
        month_start = date(local_today.year, local_today.month, 1)
        while True:
            if _quarter_cycle_month(config.month_of_quarter, month_start.month):
                yield date(month_start.year, month_start.month, config.day_of_month)
            month_start = _add_months(month_start, 1)

    else:  # pragma: no cover - ScheduleConfig's own Literal type forbids this
        raise ValueError(f"Unknown schedule kind: {config.kind!r}.")


def compute_next_run(config: ScheduleConfig, *, tz_name: str, after: datetime) -> datetime:
    """Return the next UTC instant, strictly after ``after``, this schedule fires.

    ``after`` may be given in any timezone (including naive-as-UTC via
    ``datetime.now(timezone.utc)``); it is converted to the schedule's own
    timezone before any candidate is considered, so "strictly after" always
    means "after, in the reader's own clock."
    """

    zone = ZoneInfo(tz_name)
    reference = after.astimezone(zone) if after.tzinfo else after.replace(tzinfo=dt_timezone.utc).astimezone(zone)

    for candidate_date in _candidate_dates(config, reference.date()):
        candidate = datetime(
            candidate_date.year, candidate_date.month, candidate_date.day,
            config.hour, config.minute, tzinfo=zone,
        )
        if candidate > reference:
            return candidate.astimezone(dt_timezone.utc)
    raise AssertionError("unreachable: candidate generators never terminate")  # pragma: no cover
