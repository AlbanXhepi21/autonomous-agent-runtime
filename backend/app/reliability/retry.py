"""Small explicit retry policy; retries target transient infrastructure only."""

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

from app.reliability.contracts import FailureCategory, RuntimeFailure


@dataclass(frozen=True, slots=True)
class RetryRule:
    max_attempts: int
    initial_delay_seconds: float = 0.05
    max_delay_seconds: float = 0.5


class RetryPolicy:
    """Category and operation-specific retry policy with safe defaults."""

    def __init__(self, rules: dict[tuple[str, FailureCategory], RetryRule] | None = None) -> None:
        self._rules = rules or {
            ("llm", FailureCategory.LLM_TIMEOUT): RetryRule(3),
            ("llm", FailureCategory.LLM_RATE_LIMIT): RetryRule(3),
            ("llm", FailureCategory.LLM_PROVIDER_ERROR): RetryRule(2),
            ("llm", FailureCategory.INVALID_MODEL_OUTPUT): RetryRule(2, 0, 0),
        }

    def retry_delay(self, failure: RuntimeFailure) -> float | None:
        rule = self._rules.get((failure.source, failure.category))
        if not failure.retryable or rule is None or failure.attempt >= rule.max_attempts:
            return None
        return min(rule.initial_delay_seconds * (2 ** (failure.attempt - 1)), rule.max_delay_seconds)


def classify_llm_failure(error: BaseException, *, run_id: str, iteration: int, attempt: int) -> RuntimeFailure:
    message = str(error).lower()
    if isinstance(error, TimeoutError):
        category = FailureCategory.LLM_TIMEOUT
    elif "rate" in message and "limit" in message:
        category = FailureCategory.LLM_RATE_LIMIT
    elif isinstance(error, (ValueError, TypeError)):
        category = FailureCategory.INVALID_MODEL_OUTPUT
    else:
        category = FailureCategory.LLM_PROVIDER_ERROR
    return RuntimeFailure.from_exception(error, category=category,
        retryable=category in {FailureCategory.LLM_TIMEOUT, FailureCategory.LLM_RATE_LIMIT,
                               FailureCategory.LLM_PROVIDER_ERROR, FailureCategory.INVALID_MODEL_OUTPUT},
        source="llm", run_id=run_id, iteration=iteration, attempt=attempt)


Sleep = Callable[[float], Awaitable[None]]


async def default_sleep(delay: float) -> None:
    await asyncio.sleep(delay)
