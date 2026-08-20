"""Restricted Python analysis over one bounded runtime-managed dataset."""

from pathlib import Path
from typing import Any

from app.analytics.datasets import AnalyticsDatasetStore
from app.artifacts.store import ArtifactStore
from app.environment.python import PythonExecutor
from app.tools.base import Tool, ToolExecutionError, ToolInputError


class AnalyzeDatasetTool(Tool):
    """Reuse the V5 child-process boundary without exposing files or credentials."""

    operation_kind = "analytics_python"
    requires_run_id = True

    def __init__(self, datasets: AnalyticsDatasetStore, python_executor: PythonExecutor, artifact_store: ArtifactStore) -> None:
        self._datasets, self._python_executor, self._artifact_store = datasets, python_executor, artifact_store
        self.max_observation_length = python_executor.max_output_bytes

    @property
    def name(self) -> str: return "analyze_dataset"
    @property
    def description(self) -> str:
        return "Run restricted Python over one bounded query dataset. analytics_data contains columns and rows; use pandas/numpy/matplotlib only when SQL is not sufficient. Save charts as .png in the current directory."
    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"dataset_id": {"type": "string"}, "code": {"type": "string"}}, "required": ["dataset_id", "code"], "additionalProperties": False}

    async def execute_for_run(self, *, run_id: str | None, **arguments: Any) -> dict[str, object]:
        if not run_id:
            raise ToolInputError("Dataset analysis requires an active run.")
        dataset = self._datasets.get(run_id=run_id, dataset_id=arguments["dataset_id"])
        if dataset is None:
            raise ToolInputError("Dataset reference is unavailable, expired, or exceeds Python analysis limits.")
        output_dir = self._python_executor.workspace.root / ".runtime" / "analytics-python" / run_id
        result = await self._python_executor.execute(arguments["code"], dataset=dataset, output_directory=output_dir)
        if not result.success:
            category = "python_timeout" if result.timed_out else "analytics_python_failed"
            raise ToolExecutionError(result.error or "Analytics Python execution failed.", failure_category=category)
        artifacts = []
        for source_path in result.generated_files:
            try:
                artifact = self._artifact_store.register(run_id=run_id, source_path=source_path,
                    name=f"chart-{len(artifacts) + 1}.png", artifact_type="chart", media_type="image/png",
                    metadata={"source": "analytics_python", "dataset_id": arguments["dataset_id"]})
            except ValueError as error:
                raise ToolExecutionError("Chart artifact could not be registered.", failure_category="artifact_registration_failed") from error
            artifacts.append(artifact.model_dump(mode="json"))
        return {"stdout": result.stdout, "duration_ms": result.duration_ms, "dataset_id": arguments["dataset_id"], "artifacts": artifacts}

    async def execute(self, **arguments: Any) -> dict[str, object]:
        raise ToolInputError("Dataset analysis requires an active run.")
