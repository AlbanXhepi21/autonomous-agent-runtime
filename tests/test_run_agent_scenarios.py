"""Tests for manual scenario-selection helpers without making HTTP requests."""

import pytest

from scripts.run_agent_scenarios import (
    SCENARIOS,
    AgentScenario,
    ScenarioRunResult,
    ScenarioSelectionError,
    print_runtime_summary,
    select_scenarios,
)


def test_selects_single_scenario() -> None:
    assert [scenario.id for scenario in select_scenarios("1")] == [1]


def test_selects_comma_separated_scenarios() -> None:
    assert [scenario.id for scenario in select_scenarios("1, 3,5")] == [1, 3, 5]


def test_selects_all_scenarios() -> None:
    assert select_scenarios("all") == list(SCENARIOS)


def test_selects_scenario_range() -> None:
    assert [scenario.id for scenario in select_scenarios("2-4")] == [2, 3, 4]


def test_rejects_unknown_scenario_id() -> None:
    with pytest.raises(ScenarioSelectionError, match="Unknown scenario ID: 99"):
        select_scenarios("99")


def test_runtime_summary_displays_tool_outcomes(capsys: pytest.CaptureFixture[str]) -> None:
    print_runtime_summary(
        {
            "run_id": "b76b0071-84cf-4a8e-8918-a1e16bf960aa",
            "iteration_count": 3,
            "tool_call_count": 1,
            "recoverable_error_count": 1,
            "duplicate_action_count": 0,
            "stop_reason": "completed",
            "tools_used": ["calculator"],
            "skills_used": ["data_analysis"],
            "tool_outcomes": [
                {
                    "tool_name": "calculator",
                    "success": False,
                    "error": "Tool rejected the supplied arguments.",
                    "blocked_as_duplicate": False,
                }
            ],
        }
    )

    output = capsys.readouterr().out
    assert "Run: b76b0071" in output
    assert "Tools used: calculator" in output
    assert "calculator: failed — Tool rejected the supplied arguments." in output


def test_scenario_is_not_successful_when_runtime_stops_the_agent() -> None:
    result = ScenarioRunResult(
        scenario=AgentScenario(99, "Limited", "", "goal"),
        timestamp="2026-08-15T00:00:00+00:00",
        duration_seconds=1.0,
        http_status=200,
        response={"completed": False, "stop_reason": "max_iterations"},
        error=None,
    )

    assert result.http_succeeded
    assert not result.agent_completed
    assert not result.succeeded


def test_scenario_succeeds_when_the_agent_completes() -> None:
    result = ScenarioRunResult(
        scenario=AgentScenario(99, "Completed", "", "goal"),
        timestamp="2026-08-15T00:00:00+00:00",
        duration_seconds=1.0,
        http_status=200,
        response={"completed": True, "stop_reason": "completed"},
        error=None,
    )

    assert result.http_succeeded
    assert result.agent_completed
    assert result.succeeded
