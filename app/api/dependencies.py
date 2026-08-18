"""Construction functions for API-facing application dependencies."""

from functools import lru_cache
from pathlib import Path

from app.agent.runner import AgentRunner
from app.agent.registry import AgentRegistry
from app.agent.delegation import ParallelSubagentExecutor, SequentialSubagentExecutor
from app.agent.summarization import SummaryPolicy
from app.config import Settings
from app.environment import CommandExecutor, PythonExecutor, Workspace, WorkspaceLimits
from app.environment.repository import Repository
from app.artifacts.store import ArtifactStore, WorkspaceArtifactStore
from app.core.limits import RuntimeLimits
from app.llm.openai_client import OpenAIClient
from app.memory.base import MemoryStore
from app.memory.in_memory import InMemoryMemoryStore
from app.memory.manager import MemoryManager
from app.memory.retrieval import MemoryRetriever
from app.memory.writing import MemoryWritingPipeline
from app.skills.registry import SkillRegistry
from app.tools.calculator import CalculatorTool
from app.tools.commands import RunCommandTool
from app.tools.filesystem import ListFilesTool, ReadFileTool, WriteFileTool
from app.tools.python_exec import PythonExecTool
from app.tools.repository import GetChangedFilesTool, GetRepositoryTreeTool, GitInspectTool, SearchFilesTool
from app.tools.artifacts import RegisterArtifactTool
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry


@lru_cache
def get_settings() -> Settings:
    """Return the shared settings instance."""

    return Settings()


def get_workspace(settings: Settings | None = None) -> Workspace:
    """Build the configured filesystem boundary without exposing host paths to agents."""

    settings = settings or get_settings()
    return Workspace(
        Path(settings.agent_workspace_root),
        WorkspaceLimits(
            max_file_read_bytes=settings.max_file_read_bytes,
            max_file_write_bytes=settings.max_file_write_bytes,
            max_list_files=settings.max_list_files,
        ),
    )


def get_command_executor(
    workspace: Workspace, settings: Settings | None = None,
) -> CommandExecutor:
    """Build the argv-only command boundary using runtime-owned configuration."""

    settings = settings or get_settings()
    allowlist = tuple(
        command.strip() for command in settings.command_allowlist.split(",") if command.strip()
    )
    return CommandExecutor(
        workspace,
        allowed_commands=allowlist,
        timeout_seconds=settings.command_timeout_seconds,
        max_output_bytes=settings.max_command_output_bytes,
    )


def get_python_executor(workspace: Workspace, settings: Settings | None = None) -> PythonExecutor:
    """Build the restricted child-process Python executor from runtime settings."""

    settings = settings or get_settings()
    allowed_imports = tuple(
        module.strip() for module in settings.python_exec_allowed_imports.split(",") if module.strip()
    )
    return PythonExecutor(
        workspace,
        allowed_imports=allowed_imports,
        timeout_seconds=settings.python_exec_timeout_seconds,
        max_code_bytes=settings.max_python_code_bytes,
        max_output_bytes=settings.max_python_output_bytes,
    )


def get_repository(workspace: Workspace) -> Repository:
    """Build the bounded repository inspection layer over the shared workspace."""

    return Repository(workspace)


@lru_cache
def get_artifact_store() -> ArtifactStore:
    """Return the development workspace artifact store for API tools and downloads."""

    settings = get_settings()
    return WorkspaceArtifactStore(get_workspace(settings), max_artifact_bytes=settings.max_artifact_bytes)


def get_tool_registry(
    workspace: Workspace | None = None,
    command_executor: CommandExecutor | None = None,
    python_executor: PythonExecutor | None = None,
    repository: Repository | None = None,
    artifact_store: ArtifactStore | None = None,
) -> ToolRegistry:
    """Build the tools available to the runtime."""

    registry = ToolRegistry()
    registry.register(CalculatorTool())
    workspace = workspace or get_workspace()
    registry.register(ListFilesTool(workspace))
    registry.register(ReadFileTool(workspace))
    registry.register(WriteFileTool(workspace))
    registry.register(RunCommandTool(command_executor or get_command_executor(workspace)))
    registry.register(PythonExecTool(python_executor or get_python_executor(workspace)))
    repository = repository or get_repository(workspace)
    registry.register(GetRepositoryTreeTool(repository))
    registry.register(SearchFilesTool(repository))
    registry.register(GetChangedFilesTool(repository))
    registry.register(GitInspectTool(repository))
    registry.register(RegisterArtifactTool(artifact_store or get_artifact_store()))
    return registry


def get_skill_registry() -> SkillRegistry:
    """Build the registry of local skill instructions."""

    return SkillRegistry()


def get_agent_registry() -> AgentRegistry:
    """Build discoverable specialist definitions; this does not execute them."""

    return AgentRegistry(
        tool_registry=get_tool_registry(), skill_registry=get_skill_registry()
    )


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
    workspace = get_workspace(settings)
    tool_registry = get_tool_registry(
        workspace,
        get_command_executor(workspace, settings),
        get_python_executor(workspace, settings),
        get_repository(workspace),
        get_artifact_store(),
    )
    skill_registry = get_skill_registry()
    agent_registry = AgentRegistry(
        tool_registry=tool_registry, skill_registry=skill_registry
    )
    limits = RuntimeLimits(
        max_iterations=settings.max_agent_iterations,
        max_tool_calls=settings.max_agent_tool_calls,
        max_recoverable_errors=settings.max_agent_recoverable_errors,
        max_consecutive_duplicate_actions=settings.max_agent_consecutive_duplicate_actions,
        max_parallel_subagents=settings.max_parallel_subagents,
        max_delegations_per_run=settings.max_delegations_per_run,
        max_subagent_iterations=settings.max_subagent_iterations,
        max_agent_depth=settings.max_agent_depth,
    )
    llm_client = get_llm_client(settings)
    delegation_executor = SequentialSubagentExecutor(
        agent_registry=agent_registry,
        tool_registry=tool_registry,
        skill_registry=skill_registry,
        llm_client_factory=lambda _definition: llm_client,
        parent_limits=limits,
    )
    return AgentRunner(
        llm_client=llm_client,
        tool_registry=tool_registry,
        skill_registry=skill_registry,
        limits=limits,
        delegation_executor=delegation_executor,
        parallel_delegation_executor=ParallelSubagentExecutor(
            delegation_executor,
            max_parallel_subagents=limits.max_parallel_subagents,
        ),
        tool_executor=get_tool_executor(tool_registry),
        memory_manager=get_memory_manager(),
        memory_retriever=get_memory_retriever(),
        memory_writer=get_memory_writer(),
        agent_registry=agent_registry,
        summary_policy=SummaryPolicy(
            trigger_observations=settings.summary_trigger_observations,
            recent_observations=settings.recent_observations,
        ),
    )
