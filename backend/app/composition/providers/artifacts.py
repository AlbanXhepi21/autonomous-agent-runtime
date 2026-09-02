"""Registered artifact storage.

Both backends write bytes through the same file provider and differ only in
where the record lives, so selecting one is a configuration choice rather than
a different code path for the callers that register and download.
"""

from app.artifacts.retention import RetentionWorker
from app.artifacts.store import ArtifactStore, WorkspaceArtifactStore
from app.composition.lifecycle import provider
from app.composition.providers.environment import get_workspace
from app.composition.providers.persistence import get_runtime_database
from app.composition.providers.settings import get_settings


@provider
def get_artifact_store() -> ArtifactStore:
    """Return the configured artifact registry for API tools and downloads."""

    settings = get_settings()
    workspace = get_workspace(settings)
    if settings.artifact_backend == "in_memory":
        return WorkspaceArtifactStore(workspace, max_artifact_bytes=settings.max_artifact_bytes)

    from app.artifacts.files import WorkspaceArtifactFiles
    from app.artifacts.postgres import PostgresArtifactStore

    return PostgresArtifactStore(
        WorkspaceArtifactFiles(workspace, max_artifact_bytes=settings.max_artifact_bytes),
        get_runtime_database(),
    )


@provider
def get_retention_worker() -> RetentionWorker:
    """Return the worker a retention process runs on a fixed interval."""

    from datetime import timedelta

    from app.artifacts.files import WorkspaceArtifactFiles

    settings = get_settings()
    return RetentionWorker(
        artifacts=get_artifact_store(),
        files=WorkspaceArtifactFiles(get_workspace(settings), max_artifact_bytes=settings.max_artifact_bytes),
        max_attempts=settings.retention_max_deletion_attempts,
        stale_claim_after=timedelta(seconds=settings.worker_claim_stale_seconds),
    )
