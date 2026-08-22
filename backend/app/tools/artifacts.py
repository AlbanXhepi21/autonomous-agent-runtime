"""Explicit artifact registration tool; source edits remain ordinary workspace writes."""

from typing import Any

from app.artifacts.store import ArtifactStore
from app.tools.base import Tool, ToolInputError


class RegisterArtifactTool(Tool):
    """Copy one deliberate workspace file to the run's artifact directory."""

    operation_kind = "artifact"
    requires_run_id = True

    def __init__(self, artifact_store: ArtifactStore) -> None:
        self._artifact_store = artifact_store

    @property
    def name(self) -> str: return "register_artifact"
    @property
    def description(self) -> str: return "Register a useful workspace file as a user-consumable artifact for this run."
    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"source_path": {"type": "string"}, "name": {"type": "string"}, "artifact_type": {"type": "string"}, "media_type": {"type": "string"}, "metadata": {"type": "object"}}, "required": ["source_path"], "additionalProperties": False}

    async def execute_for_run(self, *, run_id: str | None, **arguments: Any) -> dict[str, object]:
        if not run_id:
            raise ToolInputError("Artifact registration requires an active run.")
        try:
            artifact = self._artifact_store.register(run_id=run_id, **arguments)
        except ValueError as error:
            raise ToolInputError(str(error)) from error
        return {"artifact": artifact.model_dump(mode="json")}

    async def execute(self, **arguments: Any) -> dict[str, object]:
        raise ToolInputError("Artifact registration requires an active run.")
