"""Run lifecycle coordination for the Workbench."""

from app.composition.lifecycle import provider
from app.composition.providers.analytics import get_chart_spec_store
from app.composition.providers.observability import get_trace_recorder
from app.composition.providers.persistence import get_conversation_store
from app.composition.providers.settings import get_settings
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
