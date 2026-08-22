"""The Workbench generates its types from a committed copy of the API schema.

If a route or response model changes and the snapshot is not regenerated, the
frontend keeps compiling against the previous contract and the mismatch only
appears at runtime. Regenerate with `npm run gen:api` from frontend/.
"""

import json
import logging
from pathlib import Path

import pytest

SNAPSHOT = Path(__file__).resolve().parent.parent / "frontend" / "openapi.json"


def test_committed_openapi_snapshot_matches_the_application() -> None:
    if not SNAPSHOT.exists():  # pragma: no cover - the snapshot is committed
        pytest.fail(f"{SNAPSHOT} is missing; run `npm run gen:api` from frontend/.")

    # Importing app.main runs configure_logging at module scope, which pins the
    # "app" logger to LOG_LEVEL and stops propagation. Tests elsewhere assert on
    # DEBUG records through caplog, and several read them with next() and no
    # default, so the leak surfaces as StopIteration rather than a clear failure.
    # Restore the logger rather than let a type snapshot break unrelated suites.
    # The import-time side effect goes away when main.py becomes a create_app
    # factory; until then this is contained here.
    logger = logging.getLogger("app")
    level, propagate, handlers = logger.level, logger.propagate, list(logger.handlers)
    try:
        from app.main import app

        current = json.loads(json.dumps(app.openapi(), sort_keys=True))
    finally:
        logger.setLevel(level)
        logger.propagate, logger.handlers = propagate, handlers

    committed = json.loads(SNAPSHOT.read_text())

    assert committed == current, (
        "The API schema changed but frontend/openapi.json was not regenerated. "
        "Run `npm run gen:api` from frontend/ and commit the result."
    )
