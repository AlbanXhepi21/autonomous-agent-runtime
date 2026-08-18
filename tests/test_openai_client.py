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
