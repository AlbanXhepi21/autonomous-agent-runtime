"""Provider-independent interface for LLM action selection."""

from abc import ABC, abstractmethod
from typing import Any

from app.agent.models import AgentAction


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
