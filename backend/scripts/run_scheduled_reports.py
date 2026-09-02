"""Run every due scheduled report, once or on a fixed interval.

Run: python -m scripts.run_scheduled_reports [--once] [--interval-seconds N]

A schedule firing goes through the same deterministic saved-report pipeline a
manual "run this report" API call uses -- see app.scheduling.worker. This
process is a thin loop around it: claim what's due, run each, sleep, repeat.
Safe to run as more than one process against the same database at once; the
claim in ScheduledReportStore.claim_due is what prevents two of them from
running the same schedule twice.

There is no supervisor in this repository yet, so this is meant to be run
either as a long-lived process under whatever process manager a deployment
already uses, or invoked with --once from an external cron.
"""

import argparse
import asyncio
import logging

from app.core.logging import configure_logging, log_event

_logger = logging.getLogger(__name__)


async def _run(*, once: bool, interval_seconds: float, batch_size: int) -> None:
    from app.composition import get_scheduler_worker, get_settings, shutdown

    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)
    worker = get_scheduler_worker()
    try:
        while True:
            outcomes = await worker.run_once(batch_size=batch_size)
            if outcomes:
                log_event(
                    _logger, logging.INFO, "scheduler_tick_completed",
                    claimed=len(outcomes),
                    completed=sum(1 for item in outcomes if item.status == "completed"),
                    failed=sum(1 for item in outcomes if item.status == "failed"),
                    skipped=sum(1 for item in outcomes if item.status == "skipped"),
                )
            if once:
                return
            await asyncio.sleep(interval_seconds)
    finally:
        await shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Run a single tick and exit.")
    parser.add_argument("--interval-seconds", type=float, default=60.0, help="Delay between ticks.")
    parser.add_argument("--batch-size", type=int, default=10, help="Schedules claimed per tick.")
    args = parser.parse_args()

    try:
        asyncio.run(_run(once=args.once, interval_seconds=args.interval_seconds, batch_size=args.batch_size))
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
