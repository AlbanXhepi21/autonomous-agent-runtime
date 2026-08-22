"""Builds the object graph the application runs on.

Kept out of app/api/ because most of what it constructs is runtime, not HTTP;
the API layer is one consumer of it rather than its owner.

Providers are grouped by area under ``providers/`` and re-exported here, so a
consumer names what it needs without depending on where it is assembled.
"""

from app.composition.lifecycle import shutdown
from app.composition.providers.analytics import (
    get_analytics_database,
    get_analytics_dataset_store,
    get_analytics_inspector,
    get_analytics_python_executor,
    get_analytics_query_executor,
    get_analytics_query_validator,
    get_chart_spec_store,
    get_metric_registry,
)
from app.composition.providers.artifacts import get_artifact_store
from app.composition.providers.environment import (
    get_command_executor,
    get_python_executor,
    get_repository,
    get_workspace,
)
from app.composition.providers.llm import get_llm_client, get_pricing_registry
from app.composition.providers.observability import get_trace_recorder
from app.composition.providers.orchestration import get_run_manager
from app.composition.providers.persistence import (
    get_conversation_store,
    get_memory_manager,
    get_memory_retriever,
    get_memory_store,
    get_memory_writer,
)
from app.composition.providers.runtime import (
    get_agent_registry,
    get_agent_runner,
    get_runtime_limits,
    get_security_policy,
    get_skill_registry,
)
from app.composition.providers.security import get_approval_store, get_credential_provider
from app.composition.providers.settings import get_settings
from app.composition.providers.tools import get_tool_executor, get_tool_registry

__all__ = [
    "get_agent_registry",
    "get_agent_runner",
    "get_analytics_database",
    "get_analytics_dataset_store",
    "get_analytics_inspector",
    "get_analytics_python_executor",
    "get_analytics_query_executor",
    "get_analytics_query_validator",
    "get_approval_store",
    "get_artifact_store",
    "get_chart_spec_store",
    "get_command_executor",
    "get_conversation_store",
    "get_credential_provider",
    "get_llm_client",
    "get_memory_manager",
    "get_memory_retriever",
    "get_memory_store",
    "get_memory_writer",
    "get_metric_registry",
    "get_pricing_registry",
    "get_python_executor",
    "get_repository",
    "get_run_manager",
    "get_runtime_limits",
    "get_security_policy",
    "get_settings",
    "get_skill_registry",
    "get_tool_executor",
    "get_tool_registry",
    "get_trace_recorder",
    "get_workspace",
    "shutdown",
]
