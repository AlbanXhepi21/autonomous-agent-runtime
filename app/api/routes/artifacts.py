"""Safe access to registered artifact files only."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.artifacts.store import ArtifactStore
from app.api.dependencies import get_artifact_store
from app.core.logging import log_event

router = APIRouter(prefix="/artifacts", tags=["artifacts"])
_logger = logging.getLogger(__name__)


@router.get("/{artifact_id}")
async def download_artifact(
    artifact_id: str, artifact_store: ArtifactStore = Depends(get_artifact_store),
) -> FileResponse:
    """Download a registered artifact by validated ID, never by a supplied path."""

    try:
        artifact = artifact_store.get(artifact_id)
        path = artifact_store.path_for(artifact_id)
    except ValueError:
        artifact = path = None
    if artifact is None or path is None:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    log_event(_logger, logging.INFO, "artifact_accessed", artifact_id=artifact.id, run_id=artifact.run_id)
    return FileResponse(path, media_type=artifact.media_type, filename=artifact.name)
