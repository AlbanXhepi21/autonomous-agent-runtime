"""Registered artifact storage."""

from app.artifacts.store import ArtifactStore, WorkspaceArtifactStore
from app.composition.lifecycle import provider
from app.composition.providers.environment import get_workspace
from app.composition.providers.settings import get_settings


@provider
def get_artifact_store() -> ArtifactStore:
    """Return the development workspace artifact store for API tools and downloads."""

    settings = get_settings()
    return WorkspaceArtifactStore(get_workspace(settings), max_artifact_bytes=settings.max_artifact_bytes)
