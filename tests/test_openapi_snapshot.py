"""The Workbench generates its types from a committed copy of the API schema.

If a route or response model changes and the snapshot is not regenerated, the
frontend keeps compiling against the previous contract and the mismatch only
appears at runtime. Regenerate with `npm run gen:api` from frontend/.
"""

import json
from pathlib import Path

import pytest

from app.main import create_app

SNAPSHOT = Path(__file__).resolve().parent.parent / "frontend" / "openapi.json"


def test_committed_openapi_snapshot_matches_the_application() -> None:
    if not SNAPSHOT.exists():  # pragma: no cover - the snapshot is committed
        pytest.fail(f"{SNAPSHOT} is missing; run `npm run gen:api` from frontend/.")

    current = json.loads(json.dumps(create_app().openapi(), sort_keys=True))
    committed = json.loads(SNAPSHOT.read_text())

    assert committed == current, (
        "The API schema changed but frontend/openapi.json was not regenerated. "
        "Run `npm run gen:api` from frontend/ and commit the result."
    )
