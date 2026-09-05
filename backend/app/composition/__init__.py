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
from app.composition.providers.artifacts import get_artifact_store, get_retention_worker
from app.composition.providers.audit import get_audit_log_store
from app.composition.providers.datasources import (
    get_data_source_onboarding_service,
    get_data_source_runtime_pool,
    get_data_source_store,
    get_secret_cipher,
)
from app.composition.providers.delivery import (
    get_delivery_providers,
    get_delivery_service,
    get_delivery_store,
    get_email_delivery_provider,
    get_link_delivery_provider,
    get_webhook_delivery_provider,
)
from app.composition.providers.environment import (
    get_command_executor,
    get_python_executor,
    get_repository,
    get_workspace,
)
from app.composition.providers.identity import (
    get_auth_service,
    get_email_sender,
    get_identity_token_store,
    get_password_hasher,
    get_rate_limiter,
    get_session_store,
    get_user_store,
)
from app.composition.providers.llm import get_llm_client, get_pricing_registry
from app.composition.providers.observability import get_trace_recorder
from app.composition.providers.orchestration import (
    get_metric_runner,
    get_report_publisher,
    get_report_rerun_service,
    get_report_template_registry,
    get_run_manager,
    get_saved_report_execution_service,
)
from app.composition.providers.persistence import (
    get_conversation_store,
    get_memory_manager,
    get_memory_retriever,
    get_memory_store,
    get_memory_writer,
    get_runtime_database,
    get_saved_report_store,
)
from app.composition.providers.runtime import (
    build_agent_runner,
    get_agent_registry,
    get_agent_runner,
    get_runtime_limits,
    get_security_policy,
    get_skill_registry,
)
from app.composition.providers.scheduling import get_scheduled_report_store, get_scheduler_worker
from app.composition.providers.security import get_approval_store, get_credential_provider
from app.composition.providers.settings import get_settings
from app.composition.providers.tenancy import (
    get_invitation_store,
    get_membership_store,
    get_report_preferences_store,
    get_tenancy_service,
    get_workspace_store,
)
from app.composition.providers.tools import get_tool_executor, get_tool_registry

__all__ = [
    "build_agent_runner",
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
    "get_audit_log_store",
    "get_auth_service",
    "get_chart_spec_store",
    "get_command_executor",
    "get_conversation_store",
    "get_credential_provider",
    "get_data_source_onboarding_service",
    "get_data_source_runtime_pool",
    "get_data_source_store",
    "get_delivery_providers",
    "get_delivery_service",
    "get_delivery_store",
    "get_email_delivery_provider",
    "get_email_sender",
    "get_identity_token_store",
    "get_link_delivery_provider",
    "get_llm_client",
    "get_memory_manager",
    "get_memory_retriever",
    "get_memory_store",
    "get_memory_writer",
    "get_metric_registry",
    "get_password_hasher",
    "get_pricing_registry",
    "get_python_executor",
    "get_rate_limiter",
    "get_repository",
    "get_runtime_database",
    "get_metric_runner",
    "get_report_publisher",
    "get_report_rerun_service",
    "get_report_template_registry",
    "get_retention_worker",
    "get_run_manager",
    "get_runtime_limits",
    "get_saved_report_execution_service",
    "get_saved_report_store",
    "get_scheduled_report_store",
    "get_scheduler_worker",
    "get_secret_cipher",
    "get_security_policy",
    "get_session_store",
    "get_settings",
    "get_skill_registry",
    "get_invitation_store",
    "get_membership_store",
    "get_report_preferences_store",
    "get_tenancy_service",
    "get_tool_executor",
    "get_tool_registry",
    "get_trace_recorder",
    "get_user_store",
    "get_webhook_delivery_provider",
    "get_workspace",
    "get_workspace_store",
    "shutdown",
]
