"""Construction functions for API-facing application dependencies."""

from functools import lru_cache

from app.agent.runner import AgentRunner
from app.config import Settings
from app.core.limits import RuntimeLimits
from app.llm.openai_client import OpenAIClient
from app.skills.registry import SkillRegistry
from app.tools.calculator import CalculatorTool
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry


@lru_cache
def get_settings() -> Settings:
    """Return the shared settings instance."""

    return Settings()


def get_tool_registry() -> ToolRegistry:
    """Build the tools available to the runtime."""

    registry = ToolRegistry()
    registry.register(CalculatorTool())
    return registry


def get_skill_registry() -> SkillRegistry:
    """Build the registry of local skill instructions."""

    return SkillRegistry()


def get_tool_executor(tool_registry: ToolRegistry | None = None) -> ToolExecutor:
    """Build the runtime boundary for executing registered tools."""

    return ToolExecutor(tool_registry or get_tool_registry())


def get_llm_client(settings: Settings | None = None) -> OpenAIClient:
    """Build the configured LLM provider implementation."""

    settings = settings or get_settings()
    return OpenAIClient(api_key=settings.openai_api_key, model=settings.openai_model)


def get_agent_runner() -> AgentRunner:
    """Build the runtime used by the agent API route."""

    settings = get_settings()
    tool_registry = get_tool_registry()
    return AgentRunner(
        llm_client=get_llm_client(settings),
        tool_registry=tool_registry,
        skill_registry=get_skill_registry(),
        limits=RuntimeLimits(
            max_iterations=settings.max_agent_iterations,
            max_tool_calls=settings.max_agent_tool_calls,
            max_recoverable_errors=settings.max_agent_recoverable_errors,
            max_consecutive_duplicate_actions=settings.max_agent_consecutive_duplicate_actions,
        ),
        tool_executor=get_tool_executor(tool_registry),
    )
