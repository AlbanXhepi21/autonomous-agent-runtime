"""The agent runtime and the capability registries it is scoped to."""

from app.composition.providers.artifacts import get_artifact_store
from app.composition.providers.environment import (
    get_command_executor,
    get_python_executor,
    get_repository,
    get_workspace,
)
from app.composition.providers.llm import get_llm_client, get_pricing_registry
from app.composition.providers.observability import get_trace_recorder
from app.composition.providers.persistence import (
    get_memory_manager,
    get_memory_retriever,
    get_memory_writer,
)
from app.composition.providers.security import get_approval_store
from app.composition.providers.settings import get_settings
from app.composition.providers.tools import get_tool_executor, get_tool_registry
from app.config import Settings
from app.core.limits import RuntimeLimits
from app.runtime.delegation import ParallelSubagentExecutor, SequentialSubagentExecutor
from app.runtime.registry import AgentRegistry
from app.runtime.runner import AgentRunner
from app.runtime.summarization import SummaryPolicy
from app.security import RiskClassifier, SecurityEnvironment, SecurityPolicy
from app.skills.registry import SkillRegistry


def get_skill_registry() -> SkillRegistry:
    """Build the registry of local skill instructions."""

    return SkillRegistry()


def get_agent_registry(tool_registry=None, skill_registry=None) -> AgentRegistry:
    """Build discoverable specialist definitions; this does not execute them."""

    return AgentRegistry(
        tool_registry=tool_registry or get_tool_registry(),
        skill_registry=skill_registry or get_skill_registry(),
    )


def get_runtime_limits(settings: Settings | None = None) -> RuntimeLimits:
    """Translate configured ceilings into the limits the runtime enforces."""

    settings = settings or get_settings()
    return RuntimeLimits(
        max_iterations=settings.max_agent_iterations,
        max_tool_calls=settings.max_agent_tool_calls,
        max_recoverable_errors=settings.max_agent_recoverable_errors,
        max_consecutive_duplicate_actions=settings.max_agent_consecutive_duplicate_actions,
        max_parallel_subagents=settings.max_parallel_subagents,
        max_delegations_per_run=settings.max_delegations_per_run,
        max_subagent_iterations=settings.max_subagent_iterations,
        max_agent_depth=settings.max_agent_depth,
    )


def get_security_policy(settings: Settings | None = None) -> SecurityPolicy:
    """Return the primary policy with human approval required for gated actions."""

    settings = settings or get_settings()
    return SecurityPolicy.primary(
        risk_classifier=RiskClassifier(SecurityEnvironment(settings.security_environment))
    ).with_human_approval_gates()


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
    agent_registry = get_agent_registry(tool_registry, skill_registry)
    limits = get_runtime_limits(settings)
    llm_client = get_llm_client(settings)
    security_policy = get_security_policy(settings)
    delegation_executor = SequentialSubagentExecutor(
        agent_registry=agent_registry,
        tool_registry=tool_registry,
        skill_registry=skill_registry,
        llm_client_factory=lambda _definition: llm_client,
        parent_limits=limits,
        security_policy=security_policy,
        approval_store=get_approval_store(),
        trace_recorder=get_trace_recorder(),
    )
    return AgentRunner(
        llm_client=llm_client,
        tool_registry=tool_registry,
        skill_registry=skill_registry,
        limits=limits,
        delegation_executor=delegation_executor,
        parallel_delegation_executor=ParallelSubagentExecutor(
            delegation_executor, max_parallel_subagents=limits.max_parallel_subagents
        ),
        tool_executor=get_tool_executor(tool_registry, security_policy),
        security_policy=security_policy,
        approval_store=get_approval_store(),
        memory_manager=get_memory_manager(),
        memory_retriever=get_memory_retriever(),
        memory_writer=get_memory_writer(),
        agent_registry=agent_registry,
        summary_policy=SummaryPolicy(
            trigger_observations=settings.summary_trigger_observations,
            recent_observations=settings.recent_observations,
        ),
        trace_recorder=get_trace_recorder(),
        pricing_registry=get_pricing_registry(),
    )
