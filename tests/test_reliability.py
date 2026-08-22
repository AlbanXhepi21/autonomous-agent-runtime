"""V7.5 bounded retry and typed-failure coverage."""

import pytest

from app.contracts.actions import AgentAction
from app.core.limits import RuntimeLimits
from app.llm.contracts import LLMClient
from app.observability import InMemoryTraceStore, TraceEventType, TraceRecorder
from app.reliability import FailureCategory, RetryPolicy, RetryRule, RuntimeFailure, classify_llm_failure
from app.security import SecurityPolicy
from app.tools.base import Tool
from app.tools.execution import ToolExecutor
from app.tools.registry import ToolRegistry
from tests.support import make_runner


class SequenceLLM(LLMClient):
    def __init__(self, values: list[object]) -> None:
        self.values = values
        self.calls = 0

    async def choose_action(self, *, system_prompt: str, context: dict[str, object]) -> AgentAction:
        value = self.values[self.calls]
        self.calls += 1
        if isinstance(value, BaseException):
            raise value
        return value  # type: ignore[return-value]


class CounterTool(Tool):
    calls = 0
    @property
    def name(self) -> str: return "counter"
    @property
    def description(self) -> str: return "Counter"
    @property
    def arguments_schema(self) -> dict: return {"type": "object", "properties": {}, "additionalProperties": False}
    async def execute(self, **arguments: object) -> str:
        self.calls += 1
        return "ran"


@pytest.mark.asyncio
async def test_timeout_retries_with_bounded_backoff_and_trace_attempts() -> None:
    sleeper: list[float] = []
    async def sleep(delay: float) -> None: sleeper.append(delay)
    recorder = TraceRecorder(InMemoryTraceStore())
    llm = SequenceLLM([TimeoutError("temporary"), AgentAction(action_type="finish", reasoning_summary="", final_answer="Done")])
    runner = make_runner(llm, limits=RuntimeLimits(), trace_recorder=recorder, retry_sleep=sleep)
    state = await runner.run("Retry")
    trace = recorder.get_trace(state.run_id)
    assert state.completed and sleeper == [0.05] and llm.calls == 2
    assert trace.metrics.llm_calls == 2  # type: ignore[union-attr]
    assert {event.event_type for event in trace.events} >= {TraceEventType.RETRY_SCHEDULED, TraceEventType.RETRY_STARTED, TraceEventType.RETRY_SUCCEEDED}  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_invalid_output_repair_is_bounded_and_permanent_error_exhausts() -> None:
    sleeps: list[float] = []
    async def sleep(delay: float) -> None: sleeps.append(delay)
    repaired = make_runner(SequenceLLM([object(), AgentAction(action_type="finish", reasoning_summary="", final_answer="Done")]), retry_sleep=sleep)
    assert (await repaired.run("Repair")).completed and sleeps == [0]

    exhausted = make_runner(SequenceLLM([TimeoutError("x"), TimeoutError("x"), TimeoutError("x")]), retry_sleep=sleep)
    with pytest.raises(TimeoutError):
        await exhausted.run("Exhaust")


def test_retry_policy_and_taxonomy_never_retry_security_or_validation() -> None:
    policy = RetryPolicy({("llm", FailureCategory.LLM_TIMEOUT): RetryRule(2, 0.1, 0.1)})
    timeout = classify_llm_failure(TimeoutError("x"), run_id="r", iteration=1, attempt=1)
    assert timeout.category is FailureCategory.LLM_TIMEOUT and policy.retry_delay(timeout) == 0.1
    security = RuntimeFailure(category=FailureCategory.SECURITY_DENIAL, message="denied", retryable=False, source="tool")
    validation = RuntimeFailure(category=FailureCategory.TOOL_VALIDATION_ERROR, message="bad", retryable=False, source="tool")
    assert policy.retry_delay(security) is None and policy.retry_delay(validation) is None


@pytest.mark.asyncio
async def test_security_policy_failure_fails_closed_without_retry() -> None:
    class BrokenPolicy(SecurityPolicy):
        def evaluate(self, *args: object, **kwargs: object): raise RuntimeError("policy unavailable")
    tool = CounterTool(); registry = ToolRegistry(); registry.register(tool)
    recorder = TraceRecorder(InMemoryTraceStore())
    result = await ToolExecutor(registry, security_policy=BrokenPolicy(), trace_recorder=recorder).execute("counter", run_id="run")
    assert not result.success and tool.calls == 0 and result.metadata["failure_category"] == "policy_failure"
