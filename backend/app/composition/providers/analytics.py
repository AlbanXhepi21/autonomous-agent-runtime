"""The external analytics database and everything read through it."""

from app.analytics import AnalyticsDatabase, PostgreSQLInspector
from app.analytics.presentation.chart_store import ChartSpecStore
from app.analytics.schema.allowlist import AnalyticsSchemaPolicy
from app.analytics.semantics.datasets import AnalyticsDatasetStore
from app.analytics.semantics.metrics import MetricRegistry
from app.analytics.sql import AnalyticsSQLExecutor, PostgreSQLQueryValidator
from app.analytics.sql.limits import AnalyticsQueryLimits
from app.composition.lifecycle import provider
from app.composition.providers.environment import get_workspace
from app.composition.providers.settings import get_settings
from app.environment import PythonExecutor

# Analysis code runs against dataframes, so it needs imports the general-purpose
# executor does not grant.
ANALYTICS_PYTHON_IMPORTS = (
    "math", "statistics", "json", "datetime", "collections", "pandas", "numpy", "matplotlib",
)


@provider
def get_analytics_database() -> AnalyticsDatabase:
    """Build the external analytics source independently of runtime persistence."""

    return AnalyticsDatabase(get_settings().analytics_database_url)


@provider
def get_analytics_inspector() -> PostgreSQLInspector:
    settings = get_settings()
    return PostgreSQLInspector(
        get_analytics_database(),
        AnalyticsSchemaPolicy.configured(settings.analytics_db_schema),
        cache_ttl_seconds=settings.analytics_schema_cache_ttl_seconds,
    )


@provider
def get_analytics_query_validator() -> PostgreSQLQueryValidator:
    return PostgreSQLQueryValidator(AnalyticsSchemaPolicy.configured(get_settings().analytics_db_schema))


@provider
def get_analytics_query_executor() -> AnalyticsSQLExecutor:
    settings = get_settings()
    return AnalyticsSQLExecutor(
        get_analytics_database(),
        AnalyticsQueryLimits(
            max_result_rows=settings.analytics_max_result_rows,
            max_result_bytes=settings.analytics_max_result_bytes,
            timeout_seconds=settings.analytics_query_timeout_seconds,
        ),
    )


@provider
def get_analytics_dataset_store() -> AnalyticsDatasetStore:
    settings = get_settings()
    return AnalyticsDatasetStore(
        max_rows=settings.analytics_python_max_dataset_rows,
        max_bytes=settings.analytics_python_max_dataset_bytes,
    )


@provider
def get_chart_spec_store() -> ChartSpecStore:
    """Runtime store for specs that will be persisted with completed runs."""

    return ChartSpecStore()


@provider
def get_metric_registry() -> MetricRegistry:
    return MetricRegistry()


def get_analytics_python_executor() -> PythonExecutor:
    settings = get_settings()
    return PythonExecutor(
        get_workspace(settings),
        allowed_imports=ANALYTICS_PYTHON_IMPORTS,
        timeout_seconds=settings.analytics_python_timeout_seconds,
        max_code_bytes=settings.max_python_code_bytes,
        max_output_bytes=settings.max_python_output_bytes,
    )
