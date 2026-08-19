"""Safe, typed failure contracts used by runtime retry decisions."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.logging import safe_error_message, safe_log_value


class FailureCategory(StrEnum):
    LLM_PROVIDER_ERROR = "llm_provider_error"
    LLM_TIMEOUT = "llm_timeout"
    LLM_RATE_LIMIT = "llm_rate_limit"
    INVALID_MODEL_OUTPUT = "invalid_model_output"
    TOOL_FAILURE = "tool_failure"
    TOOL_TIMEOUT = "tool_timeout"
    TOOL_VALIDATION_ERROR = "tool_validation_error"
    MEMORY_FAILURE = "memory_failure"
    DATABASE_FAILURE = "database_failure"
    SUBAGENT_FAILURE = "subagent_failure"
    SUBAGENT_TIMEOUT = "subagent_timeout"
    APPROVAL_TIMEOUT = "approval_timeout"
    SECURITY_DENIAL = "security_denial"
    POLICY_FAILURE = "policy_failure"
    RUNTIME_LIMIT = "runtime_limit"
    UNKNOWN_FAILURE = "unknown_failure"


class RuntimeFailure(BaseModel):
    """Sanitized operational failure; never a stack trace or model-facing detail."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: FailureCategory
    message: str
    retryable: bool
    source: str
    run_id: str | None = None
    iteration: int | None = Field(default=None, ge=0)
    attempt: int = Field(default=1, ge=1)
    cause_metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_exception(cls, error: BaseException, *, category: FailureCategory, retryable: bool,
                       source: str, run_id: str | None = None, iteration: int | None = None,
                       attempt: int = 1) -> "RuntimeFailure":
        return cls(category=category, message=safe_error_message(error), retryable=retryable,
            source=source, run_id=run_id, iteration=iteration, attempt=attempt,
            cause_metadata={"error_type": type(error).__name__})
