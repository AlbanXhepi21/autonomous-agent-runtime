"""The capabilities available to the runtime, and the boundary that runs them."""

from app.artifacts.store import ArtifactStore
from app.composition.providers.analytics import (
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
from app.composition.providers.observability import get_trace_recorder
from app.composition.providers.settings import get_settings
from app.environment import CommandExecutor, PythonExecutor, Workspace
from app.environment.repository import Repository
from app.security import SecurityPolicy
from app.tools.artifacts import RegisterArtifactTool
from app.tools.base import Tool
from app.tools.calculator import CalculatorTool
from app.tools.commands import RunCommandTool
from app.tools.database import (
    AnalyzeDatasetTool,
    CreateChartTool,
    DescribeMetricTool,
    DescribeTableTool,
    GenerateReportTool,
    GetTableRelationshipsTool,
    ListMetricsTool,
    ListTablesTool,
    QueryDatabaseTool,
    SearchSchemaTool,
)
from app.tools.execution import ToolExecutor
from app.tools.filesystem import ListFilesTool, ReadFileTool, WriteFileTool
from app.tools.planning import UpdateInvestigationPlanTool
from app.tools.python_exec import PythonExecTool
from app.tools.registry import ToolRegistry
from app.tools.repository import (
    GetChangedFilesTool,
    GetRepositoryTreeTool,
    GitInspectTool,
    SearchFilesTool,
)


def get_tool_registry(
    workspace: Workspace | None = None,
    command_executor: CommandExecutor | None = None,
    python_executor: PythonExecutor | None = None,
    repository: Repository | None = None,
    artifact_store: ArtifactStore | None = None,
    analytics_tools: dict[str, Tool] | None = None,
) -> ToolRegistry:
    """Build the tools available to the runtime.

    ``analytics_tools``, when given, replaces the five demo-database analytics
    tools (list_tables, describe_table, search_schema, get_table_relationships,
    query_database) with a workspace's own governed set -- see
    ``app.datasources.agent_integration.resolve_workspace_tools``. Everything
    else about the registry (files, commands, repository, artifacts, charts,
    metrics) is unchanged either way.
    """

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
    artifacts = artifact_store or get_artifact_store()
    registry.register(RegisterArtifactTool(artifacts))
    if analytics_tools is not None:
        for tool in analytics_tools.values():
            registry.register(tool)
    else:
        inspector = get_analytics_inspector()
        registry.register(ListTablesTool(inspector))
        registry.register(DescribeTableTool(inspector))
        registry.register(GetTableRelationshipsTool(inspector))
        registry.register(SearchSchemaTool(inspector))
        registry.register(
            QueryDatabaseTool(
                inspector,
                get_analytics_query_validator(),
                get_analytics_query_executor(),
                get_analytics_dataset_store(),
            )
        )
    registry.register(
        AnalyzeDatasetTool(get_analytics_dataset_store(), get_analytics_python_executor(), artifacts)
    )
    registry.register(CreateChartTool(get_chart_spec_store(), get_analytics_dataset_store()))
    registry.register(GenerateReportTool(get_analytics_dataset_store(), workspace, artifacts))
    registry.register(ListMetricsTool(get_metric_registry()))
    registry.register(DescribeMetricTool(get_metric_registry()))
    registry.register(UpdateInvestigationPlanTool())
    return registry


def get_tool_executor(
    tool_registry: ToolRegistry | None = None, security_policy: SecurityPolicy | None = None
) -> ToolExecutor:
    """Build the runtime boundary for executing registered tools."""

    settings = get_settings()
    return ToolExecutor(
        tool_registry or get_tool_registry(),
        security_policy=security_policy or SecurityPolicy.primary(),
        trace_recorder=get_trace_recorder(),
        expose_sql=settings.analytics_ui_expose_sql,
        max_sql_chars=settings.analytics_ui_max_sql_chars,
    )
