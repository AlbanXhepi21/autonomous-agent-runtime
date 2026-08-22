"""Tests for OpenAI function-call parsing without network access."""

import json
from types import SimpleNamespace

import pytest

from app.llm.openai_client import OpenAIClient


class FakeResponses:
    """Capture the SDK request and return a valid function call."""

    def __init__(self) -> None:
        self.request: dict[str, object] | None = None

    async def create(self, **kwargs: object) -> SimpleNamespace:
        self.request = kwargs
        return SimpleNamespace(
            model="gpt-5.4-mini-2026-03-17",
            usage=SimpleNamespace(
                input_tokens=100,
                output_tokens=20,
                input_tokens_details=SimpleNamespace(cached_tokens=10),
                output_tokens_details=SimpleNamespace(reasoning_tokens=4),
            ),
            output=[
                SimpleNamespace(
                    type="function_call",
                    name="tool_calculator",
                    arguments=json.dumps(
                        {
                            "expression": "1 + 1",
                            "reasoning_summary": "Compute the expression.",
                        }
                    ),
                )
            ]
        )


@pytest.mark.asyncio
async def test_openai_client_parses_tool_function_call() -> None:
    client = OpenAIClient(api_key="test-key", model="test-model")
    responses = FakeResponses()
    client._client = SimpleNamespace(responses=responses)  # type: ignore[assignment]

    action = await client.choose_action(
        system_prompt="Choose an action.",
        context={
            "available_tools": [
                {
                    "name": "calculator",
                    "description": "Evaluate arithmetic.",
                    "arguments_schema": {
                        "type": "object",
                        "properties": {"expression": {"type": "string"}},
                        "required": ["expression"],
                        "additionalProperties": False,
                    },
                }
            ],
            "available_skills": [{"name": "research"}],
        },
    )

    assert action.tool_arguments == {"expression": "1 + 1"}
    assert responses.request is not None
    assert responses.request["tool_choice"] == "required"
    assert responses.request["parallel_tool_calls"] is False
    functions = responses.request["tools"]
    assert isinstance(functions, list)
    assert {function["name"] for function in functions} == {
        "tool_calculator",
        "load_skill",
        "finish",
    }
    assert all(function["strict"] is True for function in functions)


@pytest.mark.asyncio
async def test_openai_client_uses_response_model_and_usage() -> None:
    client = OpenAIClient(api_key="test-key", model="requested-model")
    client._client = SimpleNamespace(responses=FakeResponses())  # type: ignore[assignment]
    decision = await client.choose_decision(system_prompt="Choose.", context={"available_tools": [], "available_skills": []})
    assert decision.model == "gpt-5.4-mini-2026-03-17"
    assert decision.usage is not None
    assert (decision.usage.input_tokens, decision.usage.cached_input_tokens, decision.usage.output_tokens) == (100, 10, 20)


def test_openai_client_exposes_and_parses_delegate_function() -> None:
    functions = OpenAIClient(api_key="test-key", model="test-model")._function_definitions(
        {
            "available_tools": [],
            "available_skills": [],
            "available_specialist_agents": [
                {"name": "research", "description": "Gather evidence."}
            ],
        }
    )

    delegate = next(function for function in functions if function["name"] == "delegate")
    assert delegate["parameters"]["properties"]["agent_name"]["enum"] == ["research"]
    action = OpenAIClient._to_agent_action(
        "delegate",
        {
            "agent_name": "research",
            "objective": "Check the licensing terms.",
            "context": "Commercial use.",
            "reasoning_summary": "Independent evidence is useful.",
        },
    )
    assert action.action_type == "delegate"
    assert action.agent_name == "research"
    assert action.objective == "Check the licensing terms."


def test_openai_client_makes_optional_tool_arguments_nullable_for_strict_mode() -> None:
    function = OpenAIClient._tool_function({
        "name": "list_files", "description": "List files.",
        "arguments_schema": {
            "type": "object", "properties": {"path": {"type": "string"}, "recursive": {"type": "boolean"}},
            "required": [], "additionalProperties": False,
        },
    })
    parameters = function["parameters"]
    assert parameters["required"] == ["path", "recursive", "reasoning_summary"]
    assert parameters["properties"]["path"]["type"] == ["string", "null"]
    action = OpenAIClient._to_agent_action("tool_list_files", {"path": None, "recursive": None, "reasoning_summary": "Inspect workspace."})
    assert action.tool_arguments == {}


def test_openai_client_accepts_function_calls_without_public_trace_summary() -> None:
    """Missing optional trace metadata must not fail an otherwise valid run."""

    action = OpenAIClient._to_agent_action(
        "finish",
        {"final_answer": "Monthly revenue is available in the chart."},
    )

    assert action.action_type == "finish"
    assert action.final_answer == "Monthly revenue is available in the chart."
    assert action.reasoning_summary == ""


def test_openai_client_disables_provider_strict_mode_for_free_form_object_tools() -> None:
    function = OpenAIClient._tool_function({
        "name": "generate_report", "description": "Generate a report.",
        "arguments_schema": {"type": "object", "properties": {"report": {"type": "object"}}, "required": ["report"], "additionalProperties": False},
    })
    assert function["strict"] is False


def test_openai_client_disables_provider_strict_mode_for_unconstrained_arrays() -> None:
    function = OpenAIClient._tool_function({
        "name": "run_command", "description": "Run a command.",
        "arguments_schema": {"type": "object", "properties": {"args": {"type": "array"}}, "required": [], "additionalProperties": False},
    })
    assert function["strict"] is False


def test_openai_client_exposes_and_parses_parallel_delegate_function() -> None:
    client = OpenAIClient(api_key="test-key", model="test-model")
    functions = client._function_definitions(
        {
            "available_tools": [],
            "available_skills": [],
            "available_specialist_agents": [{"name": "research"}, {"name": "data_analyst"}],
            "runtime_status": {"max_parallel_subagents": 2},
        }
    )

    parallel = next(function for function in functions if function["name"] == "delegate_parallel")
    assert parallel["parameters"]["properties"]["delegations"]["maxItems"] == 2
    action = client._to_agent_action(
        "delegate_parallel",
        {
            "reasoning_summary": "The objectives are independent.",
            "delegations": [
                {"agent_name": "research", "objective": "Check licenses."},
                {"agent_name": "data_analyst", "objective": "Analyze costs."},
            ],
        },
    )
    assert action.action_type == "delegate_parallel"
    assert [item.agent_name for item in action.delegations] == ["research", "data_analyst"]
