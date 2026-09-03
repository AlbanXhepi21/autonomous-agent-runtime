"""Safe access to registered artifact files only.

Unlike every other tenant-scoped router, this one keeps a bare
``/artifacts/{id}`` shape rather than nesting under
``/api/v1/workspaces/{workspace_id}``: delivery emails and webhooks
(``app.delivery.providers``) embed exactly that link for a recipient who may
have no other context, and changing the shape would break every link
already sent. Authorization is therefore done by hand in each route --
resolve the artifact's owning workspace from its ID first (``get_by_id``,
deliberately unscoped -- see its docstring), then verify the caller
actually has standing there -- rather than through the usual
``require_permission``/``get_tenant_context`` dependency, which needs a
``workspace_id`` this router's URLs don't carry.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.artifacts.store import ArtifactStore
from app.composition import get_artifact_store, get_tenancy_service
from app.core.logging import log_event
from app.identity.contracts import User
from app.tenancy.permissions import Permission
from app.tenancy.service import (
    MembershipDisabledError,
    MembershipNotFoundError,
    TenancyService,
    WorkspaceInactiveError,
    WorkspaceNotFoundError,
)

router = APIRouter(prefix="/artifacts", tags=["artifacts"])
_logger = logging.getLogger(__name__)


async def _verify_membership(tenancy: TenancyService, *, user: User, workspace_id: UUID) -> None:
    """Raise 404 unless ``user`` is an active, reading-permitted member of ``workspace_id``.

    404 rather than 403 for every failure mode here, matching
    ``get_tenant_context``: a caller with no standing in the artifact's
    workspace should not be able to tell "no such artifact" apart from
    "exists, but not yours."
    """

    try:
        context = await tenancy.get_context(user=user, workspace_id=workspace_id)
    except (WorkspaceNotFoundError, WorkspaceInactiveError, MembershipNotFoundError, MembershipDisabledError) as error:
        raise HTTPException(status_code=404, detail="Artifact not found.") from error
    if not context.has_permission(Permission.READ_TENANT_RESOURCES):
        raise HTTPException(status_code=404, detail="Artifact not found.")


@router.get("/{artifact_id}")
async def download_artifact(
    artifact_id: str,
    user: User = Depends(get_current_user),
    artifact_store: ArtifactStore = Depends(get_artifact_store),
    tenancy: TenancyService = Depends(get_tenancy_service),
) -> FileResponse:
    """Download a registered artifact by validated ID, never by a supplied path."""

    try:
        artifact = await artifact_store.get_by_id(artifact_id=artifact_id)
    except ValueError:
        artifact = None
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    await _verify_membership(tenancy, user=user, workspace_id=artifact.workspace_id)
    path = await artifact_store.path_for(workspace_id=artifact.workspace_id, artifact_id=artifact_id)
    if path is None:
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
async def list_artifacts(
    workspace_id: UUID,
    run_id: str | None = None,
    user: User = Depends(get_current_user),
    artifact_store: ArtifactStore = Depends(get_artifact_store),
    tenancy: TenancyService = Depends(get_tenancy_service),
) -> list[ArtifactMetadata]:
    """Unlike download/preview, this always has a caller-supplied workspace in
    hand already (there is no single artifact ID to discover one from) --
    still verified the same way, never trusted outright.
    """

    await _verify_membership(tenancy, user=user, workspace_id=workspace_id)
    return [_metadata(artifact) for artifact in await artifact_store.list(workspace_id=workspace_id, run_id=run_id)]


@router.get("/{artifact_id}/preview")
async def preview_artifact(
    artifact_id: str,
    user: User = Depends(get_current_user),
    artifact_store: ArtifactStore = Depends(get_artifact_store),
    tenancy: TenancyService = Depends(get_tenancy_service),
):
    """Return only bounded, non-executable previews of registered artifacts."""

    try:
        artifact = await artifact_store.get_by_id(artifact_id=artifact_id)
    except ValueError:
        artifact = None
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    await _verify_membership(tenancy, user=user, workspace_id=artifact.workspace_id)
    path = await artifact_store.path_for(workspace_id=artifact.workspace_id, artifact_id=artifact_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    if artifact.media_type.startswith("image/") and artifact.media_type in {"image/png", "image/jpeg"}:
        return FileResponse(path, media_type=artifact.media_type)
    if artifact.media_type in {"text/markdown", "text/csv", "application/json", "text/plain"}:
        content = path.read_text(encoding="utf-8", errors="replace")[:65_536]
        return JSONResponse({"content": content, "truncated": path.stat().st_size > 65_536, "media_type": artifact.media_type})
    raise HTTPException(status_code=415, detail="Artifact preview is not supported.")
