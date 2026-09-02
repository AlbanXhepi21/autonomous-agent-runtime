"""Scheduled execution, retention and delivery must never reach an LLM.

A schedule firing goes through the same deterministic pipeline a manual
saved-report run does; a retention sweep and a delivery attempt are pure
infrastructure operations. None of the three has any legitimate reason to
import anything under ``app.llm`` or to be able to start a new agent run --
asserted here transitively, not just by inspecting each module's own
imports, so a future indirect import cannot quietly reopen the boundary.
"""

import ast
from collections import deque
from pathlib import Path

import pytest

from tests.support import BACKEND_ROOT

APP = BACKEND_ROOT / "app"


def _module_path(name: str) -> Path | None:
    base = BACKEND_ROOT / name.replace(".", "/")
    for candidate in (base.with_suffix(".py"), base / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


def _imports(name: str) -> set[str]:
    path = _module_path(name)
    if path is None:
        return set()
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app."):
            found.add(node.module)
        elif isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names if alias.name.startswith("app.")}
    return found


def _reachable(start: str) -> set[str]:
    seen: set[str] = set()
    queue = deque([start])
    while queue:
        name = queue.popleft()
        if name in seen:
            continue
        seen.add(name)
        queue.extend(_imports(name))
    return seen


@pytest.mark.parametrize(
    "module",
    [
        "app.scheduling.worker",
        "app.scheduling.calculator",
        "app.scheduling.store",
        "app.artifacts.retention",
        "app.delivery.service",
        "app.delivery.providers",
        "app.delivery.store",
    ],
)
def test_no_module_reaches_the_llm_provider(module: str) -> None:
    reachable = _reachable(module)

    assert module in reachable
    llm_reachable = [name for name in reachable if name.startswith("app.llm")]
    assert not llm_reachable, f"{module} can reach the LLM provider package via {llm_reachable}"


def test_the_scheduler_cannot_reach_the_agent_run_manager() -> None:
    """A schedule firing must never be how a new agent investigation starts."""

    assert "app.orchestration.run_manager" not in _reachable("app.scheduling.worker")


def test_the_retention_worker_touches_only_artifacts_and_logging() -> None:
    """Deleting expired bytes has no business reaching reports, scheduling, or delivery."""

    direct_imports = _imports("app.artifacts.retention")
    unexpected = [
        name for name in direct_imports
        if not (name.startswith("app.artifacts.") or name.startswith("app.core."))
    ]
    assert not unexpected, f"app.artifacts.retention imports beyond its own concern: {unexpected}"


def test_a_scheduled_report_create_request_cannot_carry_a_figure() -> None:
    """A caller names *when* to run a saved report -- never a value to display."""

    from app.api.schemas.scheduled_reports import ScheduledReportCreateRequest

    with pytest.raises(ValueError):
        ScheduledReportCreateRequest.model_validate({
            "saved_report_id": "00000000-0000-0000-0000-000000000000",
            "schedule": {"kind": "daily", "hour": 6, "minute": 0},
            "timezone": "UTC",
            "revenue": 163,
        })


def test_a_delivery_trigger_request_carries_no_provider_credential() -> None:
    """The only per-request fields are what to send and where -- never a secret."""

    from app.api.schemas.scheduled_reports import DeliveryTriggerRequest

    assert set(DeliveryTriggerRequest.model_fields) == {"artifact_id", "channel", "destination"}
