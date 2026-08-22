"""Shared test doubles and runtime construction helpers.

These live outside ``conftest.py`` so tests can import the names directly;
importing from a conftest module is discouraged by pytest. ``conftest.py``
exposes the same helpers as fixtures for tests that prefer injection.

``make_runner`` exists so that the ``AgentRunner`` signature is referenced in
one place rather than at every construction site.
"""

from pathlib import Path
from collections.abc import Iterable
from typing import Any

from app.contracts.actions import AgentAction
from app.llm.contracts import LLMClient
from app.runtime.runner import AgentRunner
from app.skills.registry import SkillRegistry
from app.tools.registry import ToolRegistry

#: Resolved here so tests can move between directories without recounting parents.
REPO_ROOT = Path(__file__).resolve().parent.parent


class ScriptedLLM(LLMClient):
    """Return a fixed sequence of actions without making network calls.

    The last action repeats once the script is exhausted, so a test only needs
    to script the actions it actually asserts on. Each context and system prompt
    handed to the provider is retained on ``contexts`` and ``prompts``, for
    assertions about what the runtime chose to expose to the model.
    """

    def __init__(self, actions: AgentAction | list[AgentAction]) -> None:
        self._actions = [actions] if isinstance(actions, AgentAction) else list(actions)
        if not self._actions:
            raise ValueError("ScriptedLLM requires at least one action.")
        self.calls = 0
        self.contexts: list[dict[str, Any]] = []
        self.prompts: list[str] = []

    async def choose_action(
        self, *, system_prompt: str, context: dict[str, Any]
    ) -> AgentAction:
        self.prompts.append(system_prompt)
        self.contexts.append(context)
        action = self._actions[min(self.calls, len(self._actions) - 1)]
        self.calls += 1
        return action


def make_runner(
    llm: LLMClient,
    tool_registry: ToolRegistry | None = None,
    skill_registry: SkillRegistry | None = None,
    **overrides: Any,
) -> AgentRunner:
    """Build an ``AgentRunner`` with empty registries unless a test supplies its own.

    Every keyword the runtime accepts passes straight through, so a test states
    only the collaborators it actually exercises.
    """

    return AgentRunner(
        llm_client=llm,
        tool_registry=tool_registry if tool_registry is not None else ToolRegistry(),
        skill_registry=skill_registry if skill_registry is not None else SkillRegistry(),
        **overrides,
    )


def logged_event(records: "Iterable[Any]", event: str) -> dict[str, Any]:
    """Return the fields of one logged event, naming it when it is absent.

    Reading caplog with next() and no default turns a missing event into
    StopIteration, and inside an async test into "coroutine raised
    StopIteration", which says nothing about what was expected.
    """

    for record in records:
        if record.getMessage() == event:
            return record.event_fields
    raise AssertionError(f"No {event!r} event was logged.")
