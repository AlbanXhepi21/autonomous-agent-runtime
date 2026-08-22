"""Shared fixtures for the test suite.

Implementations live in ``tests/support.py``; this module only exposes them as
fixtures. Tests may use either form — the fixtures suit tests that build a
runtime once, and direct imports suit tests that need several variants.
"""

from collections.abc import Callable

import pytest

from app.runtime.runner import AgentRunner
from tests.support import ScriptedLLM, make_runner


@pytest.fixture
def scripted_llm() -> type[ScriptedLLM]:
    """Return the scripted provider class so a test can script several of them."""

    return ScriptedLLM


@pytest.fixture
def runner_factory() -> Callable[..., AgentRunner]:
    """Return the runtime factory, so the constructor is named in one place."""

    return make_runner
