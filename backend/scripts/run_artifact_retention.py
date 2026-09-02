"""Delete the bytes of every expired artifact, once or on a fixed interval.

Run: python -m scripts.run_artifact_retention [--once] [--interval-seconds N]

Never removes a database row -- an expired artifact's record survives with
``status=DELETED`` as its audit trail; only the underlying file is removed.
A ``legal_hold`` or ``permanent`` artifact is never touched. Safe to run as
more than one process against the same database; see
``ArtifactStore.claim_expired`` for the claim that makes that safe.
"""

import argparse
import asyncio
import logging

from app.core.logging import configure_logging, log_event

_logger = logging.getLogger(__name__)


async def _run(*, once: bool, interval_seconds: float, batch_size: int) -> None:
    from app.composition import get_retention_worker, get_settings, shutdown

    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)
    worker = get_retention_worker()
    try:
        while True:
            outcomes = await worker.run_once(batch_size=batch_size)
            if outcomes:
                log_event(
                    _logger, logging.INFO, "retention_tick_completed",
                    claimed=len(outcomes),
                    deleted=sum(1 for item in outcomes if item.status == "deleted"),
                    failed=sum(1 for item in outcomes if item.status == "failed"),
                    gave_up=sum(1 for item in outcomes if item.status == "gave_up"),
                )
            if once:
                return
            await asyncio.sleep(interval_seconds)
    finally:
        await shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Run a single tick and exit.")
    parser.add_argument("--interval-seconds", type=float, default=300.0, help="Delay between ticks.")
    parser.add_argument("--batch-size", type=int, default=50, help="Artifacts claimed per tick.")
    args = parser.parse_args()

    try:
        asyncio.run(_run(once=args.once, interval_seconds=args.interval_seconds, batch_size=args.batch_size))
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
