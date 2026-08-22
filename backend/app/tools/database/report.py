"""Render evidence-linked reports and bounded CSV exports as artifacts."""

import csv
from pathlib import Path
from typing import Any

from app.analytics.presentation.reports import AnalyticalReport, render_markdown
from app.analytics.semantics.datasets import AnalyticsDatasetStore
from app.artifacts.store import ArtifactStore
from app.environment.workspace import Workspace
from app.tools.base import Tool, ToolExecutionError, ToolInputError


class GenerateReportTool(Tool):
    operation_kind = "analytics_report"
    requires_run_id = True
    def __init__(self, datasets: AnalyticsDatasetStore, workspace: Workspace, artifacts: ArtifactStore) -> None:
        self._datasets, self._workspace, self._artifacts = datasets, workspace, artifacts
    @property
    def name(self) -> str: return "generate_report"
    @property
    def description(self) -> str: return "Create evidence-backed Markdown/JSON report artifacts and optional bounded CSV extracts from query datasets."
    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"report": {"type": "object"}}, "required": ["report"], "additionalProperties": False}
    async def execute_for_run(self, *, run_id: str | None, **arguments: Any) -> dict[str, object]:
        if not run_id: raise ToolInputError("Report generation requires an active run.")
        try: report = AnalyticalReport.model_validate(arguments["report"])
        except Exception as error: raise ToolInputError("Report structure or evidence references are invalid.") from error
        directory = self._workspace.root / ".runtime" / "reports" / run_id
        directory.mkdir(parents=True, exist_ok=True)
        artifacts = []
        try:
            artifacts.append(self._register(run_id, directory, "report.md", render_markdown(report), "report", "text/markdown", report))
            artifacts.append(self._register(run_id, directory, "supporting_metrics.json", report.model_dump_json(indent=2), "report_data", "application/json", report))
            for index, dataset_id in enumerate(report.dataset_ids_for_csv, start=1):
                dataset = self._datasets.get(run_id=run_id, dataset_id=dataset_id)
                if dataset is None: continue
                path = directory / f"extract-{index}.csv"
                with path.open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.writer(stream); writer.writerow(dataset["columns"]); writer.writerows(dataset["rows"])
                artifacts.append(self._register_path(run_id, path, "csv_extract", "text/csv", report))
        except (OSError, ValueError) as error:
            raise ToolExecutionError("Report artifact could not be created within configured limits.", failure_category="artifact_registration_failed") from error
        return {"report_type": report.report_type.value, "time_period": report.time_period, "artifacts": artifacts, "source_query_ids": report.source_query_ids}
    def _register(self, run_id: str, directory: Path, name: str, text: str, artifact_type: str, media_type: str, report: AnalyticalReport) -> dict[str, object]:
        path = directory / name; path.write_text(text, encoding="utf-8")
        return self._register_path(run_id, path, artifact_type, media_type, report)
    def _register_path(self, run_id: str, path: Path, artifact_type: str, media_type: str, report: AnalyticalReport) -> dict[str, object]:
        artifact = self._artifacts.register(run_id=run_id, source_path=path.relative_to(self._workspace.root).as_posix(), artifact_type=artifact_type, media_type=media_type, metadata={"report_type": report.report_type.value, "time_period": report.time_period, "source_query_ids": report.source_query_ids})
        return artifact.model_dump(mode="json")
    async def execute(self, **arguments: Any) -> dict[str, object]:
        raise ToolInputError("Report generation requires an active run.")
