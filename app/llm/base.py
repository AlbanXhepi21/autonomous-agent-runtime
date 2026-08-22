"""Provider-independent interface for LLM action selection."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.actions import AgentAction


class LLMUsage(BaseModel):
    """Provider-neutral token accounting; unavailable fields remain null."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    cache_write_tokens: int | None = Field(default=None, ge=0)
    reasoning_tokens: int | None = Field(default=None, ge=0)

    @property
    def total_tokens(self) -> int | None:
        values = (self.input_tokens, self.output_tokens)
        return sum(value for value in values if value is not None) if any(value is not None for value in values) else None


class LLMDecision(BaseModel):
    """One action plus bounded provider-neutral observability metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: Any
    usage: LLMUsage | None = None
    model: str | None = Field(default=None, max_length=256)
    provider: str | None = Field(default=None, max_length=128)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class LLMClient(ABC):
    """An LLM provider that can choose the agent's next action."""

    @abstractmethod
    async def choose_action(
        self,
        *,
        system_prompt: str,
        context: dict[str, Any],
    ) -> AgentAction:
        """Produce a validated action from the current agent context."""

    async def choose_decision(self, *, system_prompt: str, context: dict[str, Any]) -> LLMDecision:
        """Optional richer path; existing deterministic clients need only implement choose_action."""

        return LLMDecision(action=await self.choose_action(system_prompt=system_prompt, context=context))
