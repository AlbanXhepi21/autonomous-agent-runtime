"""DA4 bounded SQL-result-to-Python analysis coverage."""

from pathlib import Path

import pytest

from app.analytics.schema.allowlist import AnalyticsSchemaPolicy
from app.analytics.schema.contracts import DatabaseSchemaSummary, DatabaseTable
from app.analytics.semantics.datasets import AnalyticsDatasetStore
from app.analytics.sql.contracts import SQLColumn, SQLQueryResult
from app.analytics.sql.validator import PostgreSQLQueryValidator
from app.artifacts.store import WorkspaceArtifactStore
from app.environment.python import PythonExecutor
from app.environment.workspace import Workspace
from app.observability import InMemoryTraceStore, TraceEventType, TraceRecorder
from app.tools.database.analyze import AnalyzeDatasetTool
from app.tools.database.query import QueryDatabaseTool
from app.tools.execution import ToolExecutor
from app.tools.registry import ToolRegistry


def setup_tool(tmp_path: Path) -> tuple[AnalyticsDatasetStore, AnalyzeDatasetTool, WorkspaceArtifactStore]:
    workspace = Workspace(tmp_path)
    datasets = AnalyticsDatasetStore(max_rows=10, max_bytes=2_000)
    # The first pandas and matplotlib import in a fresh environment spends a few
    # seconds compiling bytecode, so a tight bound here fails once on any cold
    # runner and passes forever after. Wide enough to survive that, tight enough
    # to still catch a hang.
    executor = PythonExecutor(workspace, allowed_imports=("pandas", "numpy", "matplotlib"), timeout_seconds=15)
    artifacts = WorkspaceArtifactStore(workspace, max_artifact_bytes=65_536)
    return datasets, AnalyzeDatasetTool(datasets, executor, artifacts), artifacts


@pytest.mark.asyncio
async def test_query_dataset_runs_statistics_and_creates_chart_artifact(tmp_path: Path) -> None:
    datasets, tool, artifacts = setup_tool(tmp_path)
    ref = datasets.register(run_id="run-1", query_id="query_001", columns=[{"name": "month"}, {"name": "revenue"}], rows=[["Jan", 10], ["Feb", 20], ["Mar", 30]])
    assert ref is not None
    registry = ToolRegistry(); registry.register(tool)
    recorder = TraceRecorder(InMemoryTraceStore())
    recorder.start_run(run_id="run-1", parent_run_id=None, agent_name="data_analyst", agent_type="specialist", goal="plot")
    code = """import pandas as pd
import matplotlib.pyplot as plt
df = pd.DataFrame(analytics_data['rows'], columns=analytics_data['columns'])
print(round(df['revenue'].mean(), 2))
plt.bar(df['month'], df['revenue'])
plt.savefig('untrusted-name.png')
"""
    result = await ToolExecutor(registry, trace_recorder=recorder).execute("analyze_dataset", {"dataset_id": ref.id, "code": code}, run_id="run-1")

    assert result.success and result.output["stdout"] == "20.0\n"
    assert result.output["artifacts"][0]["name"] == "chart-1.png"
    assert artifacts.path_for(result.output["artifacts"][0]["id"]) is not None
    trace = recorder.get_trace("run-1")
    assert trace is not None
    event_types = {event.event_type for event in trace.events}
    assert {TraceEventType.ANALYTICS_PYTHON_STARTED, TraceEventType.ANALYTICS_PYTHON_FINISHED, TraceEventType.ARTIFACT_CREATED, TraceEventType.CHART_CREATED} <= event_types


class Inspector:
    async def list_tables(self) -> DatabaseSchemaSummary:
        return DatabaseSchemaSummary(schemas=["public"], tables=[DatabaseTable(name="orders", schema="public")])


class QueryExecutor:
    async def execute(self, sql: str, *, referenced_tables: list[str]) -> SQLQueryResult:
        return SQLQueryResult(columns=[SQLColumn(name="value")], rows=[[2], [4]], row_count=2, execution_ms=1, referenced_tables=referenced_tables)


@pytest.mark.asyncio
async def test_query_result_becomes_run_scoped_python_dataset(tmp_path: Path) -> None:
    datasets, analysis_tool, artifacts = setup_tool(tmp_path)
    query_tool = QueryDatabaseTool(Inspector(), PostgreSQLQueryValidator(AnalyticsSchemaPolicy.configured("public")), QueryExecutor(), datasets)  # type: ignore[arg-type]
    registry = ToolRegistry(); registry.register(query_tool); registry.register(analysis_tool)
    executor = ToolExecutor(registry)
    query = await executor.execute("query_database", {"sql": "SELECT value FROM orders"}, run_id="run-chain")
    assert query.success and query.output["dataset"]["id"] == "dataset_query_001"
    analysis = await executor.execute("analyze_dataset", {"dataset_id": query.output["dataset"]["id"], "code": "print(sum(row[0] for row in analytics_data['rows']))"}, run_id="run-chain")
    assert analysis.success and analysis.output["stdout"] == "6\n"


@pytest.mark.asyncio
async def test_dataset_is_bounded_and_python_cannot_read_secrets_or_import_network(tmp_path: Path) -> None:
    datasets, tool, _ = setup_tool(tmp_path)
    assert datasets.register(run_id="r", query_id="query_001", columns=[{"name": "x"}], rows=[["x" * 2_000]]) is None
    ref = datasets.register(run_id="r", query_id="query_002", columns=[{"name": "x"}], rows=[[1]])
    assert ref is not None
    registry = ToolRegistry(); registry.register(tool)
    executor = ToolExecutor(registry)
    secrets = await executor.execute("analyze_dataset", {"dataset_id": ref.id, "code": "import os\nprint(os.environ)"}, run_id="r")
    network = await executor.execute("analyze_dataset", {"dataset_id": ref.id, "code": "import socket"}, run_id="r")
    assert not secrets.success and secrets.metadata["failure_category"] == "analytics_python_failed"
    assert not network.success and network.metadata["failure_category"] == "analytics_python_failed"


@pytest.mark.asyncio
async def test_analytics_python_timeout_is_safe(tmp_path: Path) -> None:
    datasets, tool, _ = setup_tool(tmp_path)
    ref = datasets.register(run_id="r", query_id="query_001", columns=[{"name": "x"}], rows=[[1]])
    assert ref is not None
    registry = ToolRegistry(); registry.register(tool)
    result = await ToolExecutor(registry).execute("analyze_dataset", {"dataset_id": ref.id, "code": "while True:\n    pass"}, run_id="r")
    assert not result.success and result.metadata["failure_category"] == "python_timeout"
