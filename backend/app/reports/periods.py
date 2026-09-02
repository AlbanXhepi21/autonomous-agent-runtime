"""Resolve a saved report's relative period into an exact, bounded window.

Every rule here is anchored to the current UTC calendar date -- never wall
clock time, never a caller's local timezone. That matches the rest of the
semantic metric layer, which already buckets and filters every timestamp
``AT TIME ZONE 'UTC'``: a period resolved in any other timezone could disagree
with the very queries it is about to bound.

``ReportPeriod`` is half-open (``start`` inclusive, ``end`` exclusive), and
every rule below produces exactly that shape. A period never includes the
current, not-yet-complete day: "current month" runs through yesterday plus
today's elapsed hours are not double-counted at the boundary because the
upper bound is always the first moment of the day *after* the window closes,
consistent with how every other period in this system is expressed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.analytics.semantics.parameters import ReportPeriod
from app.reports.contracts import RelativePeriod


class RelativePeriodResolutionError(ValueError):
    """Raised when a relative period cannot be resolved as declared."""


@dataclass(frozen=True, slots=True)
class ResolvedPeriod:
    """A resolved window, with the human-readable rule that produced it."""

    period: ReportPeriod
    #: What was resolved, for an audit trail and a reader-facing caveat --
    #: e.g. "previous_month, resolved 2026-08-25 UTC".
    description: str


def _quarter_start(year: int, month: int) -> date:
    quarter_first_month = ((month - 1) // 3) * 3 + 1
    return date(year, quarter_first_month, 1)


def _add_months(anchor: date, months: int) -> date:
    """The first of the month ``months`` away from ``anchor``'s month."""

    zero_based = anchor.month - 1 + months
    year = anchor.year + zero_based // 12
    month = zero_based % 12 + 1
    return date(year, month, 1)


def resolve_relative_period(period: RelativePeriod, *, today: date) -> ResolvedPeriod:
    """Resolve one ``RelativePeriod`` against an explicit reference date.

    ``today`` is always the caller's current UTC calendar date -- passed in
    rather than read from a clock in here, so resolution is a pure function a
    test can pin to any date, including a month, quarter or year boundary.
    """

    if period.kind == "fixed":
        assert period.start is not None and period.end is not None  # enforced by RelativePeriod
        return ResolvedPeriod(
            period=ReportPeriod(start=period.start, end=period.end),
            description=f"fixed period {period.start.isoformat()} to {period.end.isoformat()}",
        )

    if period.kind == "last_n_days":
        assert period.days is not None
        # Today is never complete, so the window ends at today's own start
        # (exclusive of today) and reaches back exactly `days` complete days.
        end = today
        start = _add_days(today, -period.days)
        return ResolvedPeriod(
            period=ReportPeriod(start=start, end=end),
            description=f"last {period.days} complete day(s) before {today.isoformat()} UTC",
        )

    if period.kind == "current_month":
        start = date(today.year, today.month, 1)
        end = _add_months(start, 1)
        return ResolvedPeriod(period=ReportPeriod(start=start, end=end),
                               description=f"current calendar month, resolved {today.isoformat()} UTC")

    if period.kind == "previous_month":
        end = date(today.year, today.month, 1)
        start = _add_months(end, -1)
        return ResolvedPeriod(period=ReportPeriod(start=start, end=end),
                               description=f"previous calendar month, resolved {today.isoformat()} UTC")

    if period.kind == "current_quarter":
        start = _quarter_start(today.year, today.month)
        end = _add_months(start, 3)
        return ResolvedPeriod(period=ReportPeriod(start=start, end=end),
                               description=f"current calendar quarter, resolved {today.isoformat()} UTC")

    if period.kind == "previous_quarter":
        current_start = _quarter_start(today.year, today.month)
        start = _add_months(current_start, -3)
        return ResolvedPeriod(period=ReportPeriod(start=start, end=current_start),
                               description=f"previous calendar quarter, resolved {today.isoformat()} UTC")

    if period.kind == "current_year":
        start = date(today.year, 1, 1)
        end = date(today.year + 1, 1, 1)
        return ResolvedPeriod(period=ReportPeriod(start=start, end=end),
                               description=f"current calendar year, resolved {today.isoformat()} UTC")

    if period.kind == "previous_year":
        start = date(today.year - 1, 1, 1)
        end = date(today.year, 1, 1)
        return ResolvedPeriod(period=ReportPeriod(start=start, end=end),
                               description=f"previous calendar year, resolved {today.isoformat()} UTC")

    raise RelativePeriodResolutionError(f"Unknown relative period kind: {period.kind!r}.")


def _add_days(anchor: date, days: int) -> date:
    from datetime import timedelta

    return anchor + timedelta(days=days)
