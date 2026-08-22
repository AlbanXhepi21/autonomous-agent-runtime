"""The public run-event vocabulary is shared across the API and the Workbench.

The server projects internal trace events onto public names, and the frontend
subscribes to those names individually. A name added on one side and not the
other produces a run whose live trace differs from the same run after a
refresh, because replayed history is not filtered by subscription. These tests
fail on either kind of drift.
"""

import re
from pathlib import Path

from app.orchestration.run_manager import _PUBLIC_EVENT_TYPES

EVENTS_TS = Path(__file__).resolve().parent.parent / "frontend" / "src" / "lib" / "api" / "events.ts"

# Emitted directly by the projection rather than mapped from a trace event.
SYNTHESISED = {"agent.started", "agent.completed"}


def frontend_event_names() -> set[str]:
    """Read the names the Workbench subscribes to, without running TypeScript."""

    source = EVENTS_TS.read_text()
    body = source.split("PUBLIC_RUN_EVENT_TYPES = [", 1)[1].split("] as const", 1)[0]
    return set(re.findall(r'"([a-z_]+\.[a-z_]+)"', body))


def test_frontend_subscribes_to_every_projected_event() -> None:
    served = set(_PUBLIC_EVENT_TYPES.values()) | SYNTHESISED

    missing = served - frontend_event_names()

    assert not missing, (
        f"The server projects {sorted(missing)} but the Workbench never subscribes, "
        "so these appear only after a refresh."
    )


def test_frontend_does_not_subscribe_to_events_the_server_cannot_send() -> None:
    served = set(_PUBLIC_EVENT_TYPES.values()) | SYNTHESISED

    unknown = frontend_event_names() - served

    assert not unknown, f"The Workbench subscribes to {sorted(unknown)}, which the server never sends."
