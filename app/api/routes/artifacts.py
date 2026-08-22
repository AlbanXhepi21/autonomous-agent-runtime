"""Safe access to registered artifact files only."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

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
class ArtifactMetadata(BaseModel):
    artifact_id: str
    run_id: str
    name: str
    type: str
    size: int
    created_at: object
    media_type: str
    metadata: dict[str, object]


def _metadata(artifact) -> ArtifactMetadata:
    return ArtifactMetadata(artifact_id=artifact.id, run_id=artifact.run_id, name=artifact.name,
                            type=artifact.artifact_type, size=artifact.size, created_at=artifact.created_at,
                            media_type=artifact.media_type, metadata=artifact.metadata)


@router.get("", response_model=list[ArtifactMetadata])
async def list_artifacts(run_id: str | None = None, artifact_store: ArtifactStore = Depends(get_artifact_store)) -> list[ArtifactMetadata]:
    return [_metadata(artifact) for artifact in artifact_store.list(run_id=run_id)]


@router.get("/{artifact_id}/preview")
async def preview_artifact(artifact_id: str, artifact_store: ArtifactStore = Depends(get_artifact_store)):
    """Return only bounded, non-executable previews of registered artifacts."""
    try: artifact, path = artifact_store.get(artifact_id), artifact_store.path_for(artifact_id)
    except ValueError: artifact = path = None
    if artifact is None or path is None: raise HTTPException(status_code=404, detail="Artifact not found.")
    if artifact.media_type.startswith("image/") and artifact.media_type in {"image/png", "image/jpeg"}:
        return FileResponse(path, media_type=artifact.media_type)
    if artifact.media_type in {"text/markdown", "text/csv", "application/json", "text/plain"}:
        content = path.read_text(encoding="utf-8", errors="replace")[:65_536]
        return JSONResponse({"content": content, "truncated": path.stat().st_size > 65_536, "media_type": artifact.media_type})
    raise HTTPException(status_code=415, detail="Artifact preview is not supported.")
