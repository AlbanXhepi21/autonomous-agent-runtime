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
