"""Construction functions for API-facing application dependencies."""

from functools import lru_cache

from app.agent.runner import AgentRunner
from app.agent.summarization import SummaryPolicy
from app.config import Settings
from app.core.limits import RuntimeLimits
from app.llm.openai_client import OpenAIClient
from app.memory.base import MemoryStore
from app.memory.in_memory import InMemoryMemoryStore
from app.memory.manager import MemoryManager
from app.memory.retrieval import MemoryRetriever
from app.memory.writing import MemoryWritingPipeline
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


@lru_cache
def get_memory_store() -> MemoryStore:
    """Build the configured storage implementation without involving the runtime."""

    settings = get_settings()
    if settings.memory_backend == "in_memory":
        return InMemoryMemoryStore()
    from app.db.session import Database
    from app.memory.postgres import PostgresMemoryStore

    return PostgresMemoryStore(Database(settings.database_url))


@lru_cache
def get_memory_manager() -> MemoryManager:
    """Return the application-scoped memory manager and its selected store."""

    return MemoryManager(get_memory_store())


@lru_cache
def get_memory_retriever() -> MemoryRetriever:
    """Return the shared selector over the configured persistent memory store."""

    return MemoryRetriever(get_memory_store())


@lru_cache
def get_memory_writer() -> MemoryWritingPipeline:
    """Return the policy-gated writer for completed-run memory candidates."""

    return MemoryWritingPipeline(get_memory_manager())


async def close_memory_resources() -> None:
    """Dispose an active PostgreSQL pool during application shutdown."""

    store = get_memory_store()
    close = getattr(store, "close", None)
    if close is not None:
        await close()
    get_memory_manager.cache_clear()
    get_memory_retriever.cache_clear()
    get_memory_writer.cache_clear()
    get_memory_store.cache_clear()


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
        memory_manager=get_memory_manager(),
        memory_retriever=get_memory_retriever(),
        memory_writer=get_memory_writer(),
        summary_policy=SummaryPolicy(
            trigger_observations=settings.summary_trigger_observations,
            recent_observations=settings.recent_observations,
        ),
    )
