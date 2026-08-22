"""Tests for the safety and capability-selection instructions."""

from app.runtime.prompt import SYSTEM_PROMPT


def test_system_prompt_establishes_agent_decision_boundaries() -> None:
    assert "own achieving the user goal" in SYSTEM_PROMPT
    assert "no predefined workflow" in SYSTEM_PROMPT
    assert "exactly one useful next action" in SYSTEM_PROMPT
    assert "Inspect observations before repeating work" in SYSTEM_PROMPT
    assert "Never fabricate tool results" in SYSTEM_PROMPT
    assert "Runtime limits are hard constraints" in SYSTEM_PROMPT
    assert "never private reasoning" in SYSTEM_PROMPT
