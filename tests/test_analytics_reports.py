"""DA5 evidence-backed report artifact coverage."""

from pathlib import Path

import pytest

from app.analytics.datasets import AnalyticsDatasetStore
from app.artifacts.store import WorkspaceArtifactStore
from app.environment.workspace import Workspace
from app.tools.database.report import GenerateReportTool
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry


def report_payload() -> dict[str, object]:
    return {"report_type": "executive", "title": "July Executive Report", "time_period": "July 2026", "executive_summary": "Revenue increased with higher order volume [query_001].", "source_query_ids": ["query_001"], "dataset_ids_for_csv": ["dataset_query_001"], "sections": [{"title": "Revenue & Growth", "metrics": [{"name": "Revenue", "value": "1200.00", "unit": "USD", "comparison": "+10% MoM", "evidence_query_ids": ["query_001"]}], "findings": [{"statement": "Orders increased.", "evidence_query_ids": ["query_001"]}]}], "recommendations": [{"action": "Monitor fulfillment capacity", "rationale": "Order volume increased.", "evidence_query_ids": ["query_001"]}], "limitations": ["Marketing attribution was not analyzed."]}


@pytest.mark.asyncio
async def test_report_generates_markdown_json_and_bounded_csv_artifacts(tmp_path: Path) -> None:
    workspace, datasets = Workspace(tmp_path), AnalyticsDatasetStore(max_rows=10, max_bytes=1000)
    assert datasets.register(run_id="r", query_id="query_001", columns=[{"name": "month"}, {"name": "revenue"}], rows=[["2026-07", "1200.00"]])
    artifacts = WorkspaceArtifactStore(workspace)
    registry = ToolRegistry(); registry.register(GenerateReportTool(datasets, workspace, artifacts))
    result = await ToolExecutor(registry).execute("generate_report", {"report": report_payload()}, run_id="r")
    assert result.success and len(result.output["artifacts"]) == 3
    markdown = next(item for item in result.output["artifacts"] if item["name"] == "report.md")
    assert "query_001" in artifacts.path_for(markdown["id"]).read_text()
    assert all(item["metadata"]["source_query_ids"] == ["query_001"] for item in result.output["artifacts"])


@pytest.mark.asyncio
async def test_report_rejects_untraceable_evidence_without_fabricating_output(tmp_path: Path) -> None:
    workspace, datasets = Workspace(tmp_path), AnalyticsDatasetStore(max_rows=10, max_bytes=1000)
    registry = ToolRegistry(); registry.register(GenerateReportTool(datasets, workspace, WorkspaceArtifactStore(workspace)))
    bad = report_payload(); bad["source_query_ids"] = ["made_up"]
    result = await ToolExecutor(registry).execute("generate_report", {"report": bad}, run_id="r")
    assert not result.success and result.metadata["failure_category"] == "tool_validation_error"
