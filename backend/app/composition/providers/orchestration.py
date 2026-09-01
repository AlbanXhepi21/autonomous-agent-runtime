"""Run lifecycle coordination for the Workbench."""

from app.analytics.presentation.templates import ReportTemplateRegistry
from app.composition.lifecycle import provider
from app.composition.providers.analytics import (
    get_analytics_inspector,
    get_analytics_query_executor,
    get_analytics_query_validator,
    get_chart_spec_store,
    get_metric_registry,
)
from app.composition.providers.artifacts import get_artifact_store
from app.composition.providers.environment import get_workspace
from app.composition.providers.observability import get_trace_recorder
from app.composition.providers.persistence import get_conversation_store
from app.composition.providers.settings import get_settings
from app.analytics.semantics.execution import MetricRunner
from app.orchestration.publishing import ReportPublisher
from app.orchestration.reruns import ReportRerunService
from app.orchestration.run_manager import AgentRunManager


@provider
def get_run_manager() -> AgentRunManager:
    """Return process-local UI run coordination over the shared trace recorder."""

    settings = get_settings()
    return AgentRunManager(
        get_trace_recorder(),
        get_conversation_store(),
        get_chart_spec_store(),
        expose_sql=settings.analytics_ui_expose_sql,
        max_sql_chars=settings.analytics_ui_max_sql_chars,
    )


@provider
def get_report_template_registry() -> ReportTemplateRegistry:
    """Discover the publishable document shapes once per process."""

    return ReportTemplateRegistry()


@provider
def get_metric_runner() -> MetricRunner:
    """Compile, validate and execute one metric request against analytics."""

    return MetricRunner(
        get_metric_registry(),
        get_analytics_query_validator(),
        get_analytics_query_executor(),
        get_analytics_inspector(),
    )


@provider
def get_report_rerun_service() -> ReportRerunService:
    """Recompute report sections without an agent turn."""

    return ReportRerunService(get_metric_runner())


@provider
def get_report_publisher() -> ReportPublisher:
    """Return the deterministic run-to-document publisher."""

    return ReportPublisher(
        get_report_template_registry(),
        get_conversation_store(),
        get_artifact_store(),
        get_workspace(get_settings()),
        get_report_rerun_service(),
    )
