"""Tests for tool registration, safe arithmetic, and structured execution."""

import logging
from typing import Any

import pytest

from app.tools.base import Tool
from app.tools.calculator import CalculatorTool
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry
from app.core.logging import PrettyEventFormatter, safe_error_message, safe_log_value


def test_tool_registry_lookup() -> None:
    calculator = CalculatorTool()
    registry = ToolRegistry()
    registry.register(calculator)

    assert registry.get("calculator") is calculator
    assert registry.definitions()[0]["name"] == "calculator"


class EchoTool(Tool):
    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Return supplied text."

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        }

    async def execute(self, **arguments: Any) -> str:
        return arguments["text"]


class FailingTool(EchoTool):
    @property
    def name(self) -> str:
        return "failing"

    async def execute(self, **arguments: Any) -> str:
        raise RuntimeError("internal details must not reach the agent")


@pytest.mark.asyncio
async def test_executor_returns_successful_structured_result() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    result = await ToolExecutor(registry).execute("echo", {"text": "hello"})

    assert result.success
    assert result.output == "hello"
    assert result.error is None
    assert result.metadata == {"tool_name": "echo"}


@pytest.mark.asyncio
async def test_executor_redacts_and_normalizes_tool_output_for_observations() -> None:
    class SensitiveOutputTool(EchoTool):
        @property
        def name(self) -> str:
            return "sensitive_output"

        async def execute(self, **arguments: Any) -> dict[str, Any]:
            return {"access_token": "private", "value": float("inf"), "object": object()}

    registry = ToolRegistry()
    registry.register(SensitiveOutputTool())

    result = await ToolExecutor(registry).execute("sensitive_output", {"text": "ignored"})

    assert result.output == {
        "access_token": "[REDACTED]",
        "value": "[non-finite number]",
        "object": "[unsupported tool output]",
    }


@pytest.mark.asyncio
async def test_executor_returns_failure_for_unknown_tool() -> None:
    result = await ToolExecutor(ToolRegistry()).execute("missing", {})

    assert not result.success
    assert result.error == "Unknown tool: missing."


@pytest.mark.asyncio
async def test_executor_redacts_sensitive_unknown_tool_names() -> None:
    result = await ToolExecutor(ToolRegistry()).execute("api_key=private-value", {})

    assert result.error == "Unknown tool: api_key=[REDACTED]"


@pytest.mark.asyncio
async def test_tool_failure_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)

    result = await ToolExecutor(ToolRegistry()).execute(
        "missing", {"access_token": "do-not-log"}, run_id="run-123", iteration=2
    )

    event = next(
        record.event_fields
        for record in caplog.records
        if record.getMessage() == "tool_execution_failed"
    )
    assert not result.success
    assert event["run_id"] == "run-123"
    assert event["iteration"] == 2
    assert event["tool"] == "missing"


def test_safe_log_value_redacts_sensitive_values_and_truncates_strings() -> None:
    value = safe_log_value(
        {
            "Authorization": "Bearer private",
            "nested": {"refresh_token": "private"},
            "text": "x" * 250,
        }
    )

    assert value["Authorization"] == "[REDACTED]"
    assert value["nested"]["refresh_token"] == "[REDACTED]"
    assert value["text"].endswith("...")
    assert len(value["text"]) == 200


def test_safe_error_message_redacts_common_secret_patterns() -> None:
    assert safe_error_message("request failed: api_key=private-value") == (
        "request failed: api_key=[REDACTED]"
    )


def test_pretty_formatter_uses_short_run_id_and_omits_null_fields() -> None:
    record = logging.LogRecord(
        "app.agent.runner",
        logging.INFO,
        __file__,
        1,
        "llm_action_selected",
        (),
        None,
    )
    record.event_fields = {
        "run_id": "b76b0071-84cf-4a8e-8918-a1e16bf960aa",
        "iteration": 1,
        "action": "load_skill",
        "skill": "research",
        "tool": None,
        "duration_ms": 1738,
    }

    rendered = PrettyEventFormatter(datefmt="%H:%M:%S").format(record)

    assert "run=b76b0071" in rendered
    assert "action=load_skill skill=research llm=1738ms" in rendered
    assert "tool=null" not in rendered


@pytest.mark.asyncio
async def test_executor_returns_failure_for_invalid_arguments() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    result = await ToolExecutor(registry).execute("echo", {})

    assert not result.success
    assert result.error == "Invalid tool arguments: missing required argument 'text'."


@pytest.mark.asyncio
async def test_executor_validates_argument_types() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    result = await ToolExecutor(registry).execute("echo", {"text": 1})

    assert not result.success
    assert result.error == "Invalid tool arguments: 'text' must be a string."


@pytest.mark.asyncio
async def test_executor_hides_tool_exceptions() -> None:
    registry = ToolRegistry()
    registry.register(FailingTool())

    result = await ToolExecutor(registry).execute("failing", {"text": "hello"})

    assert not result.success
    assert result.error == "Tool execution failed."
    assert "internal details" not in result.error


@pytest.mark.asyncio
async def test_calculator_evaluates_valid_expression() -> None:
    assert await CalculatorTool().execute(expression="(2 + 3) * 4 ** 2") == "80"


@pytest.mark.asyncio
async def test_calculator_rejects_unsafe_expression() -> None:
    with pytest.raises(ValueError, match="Invalid calculator expression"):
        await CalculatorTool().execute(expression="__import__('os').system('echo unsafe')")


@pytest.mark.asyncio
async def test_calculator_rejects_complex_results() -> None:
    with pytest.raises(ValueError, match="Invalid calculator expression"):
        await CalculatorTool().execute(expression="(-1) ** 0.5")
