"""Replaceable artifact storage rooted in the configured Workspace.

Registering is two steps on purpose: the record is created ``PENDING``, the
bytes are written and verified, and only then does the record become ``READY``.
Retrieval ignores anything that is not ready, so an interrupted write leaves an
unusable row rather than a download link to a partial file.

The methods are asynchronous because the durable registry talks to PostgreSQL.
The in-process implementation needs no I/O to satisfy them, but sharing one
contract is what lets the provider swap without changing a caller.
"""

import mimetypes
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app.artifacts.contracts import Artifact, ArtifactStatus
from app.artifacts.files import WorkspaceArtifactFiles, storage_key
from app.environment.workspace import Workspace


def validated_artifact_id(artifact_id: str) -> str:
    """Accept only an identifier this package could have issued."""

    try:
        return str(UUID(artifact_id))
    except (ValueError, TypeError) as error:
        raise ValueError("Invalid artifact ID.") from error


def validated_run_id(run_id: str) -> str:
    """Reject a run identifier that would escape its artifact directory."""

    if not run_id.strip() or Path(run_id).name != run_id or run_id in {".", ".."} or "\0" in run_id:
        raise ValueError("A run ID is required to register an artifact.")
    return run_id


def validated_filename(name: str) -> str:
    """Reject a download name that is a path rather than a filename."""

    if Path(name).name != name or name in {"", ".", ".."} or "\0" in name:
        raise ValueError("Artifact name must be a simple filename.")
    return name


class ArtifactStore(ABC):
    """Persist and retrieve metadata-backed artifacts without exposing raw paths."""

    @abstractmethod
    async def register(self, *, run_id: str, source_path: str, name: str | None = None,
                       artifact_type: str = "file", media_type: str | None = None,
                       metadata: dict[str, object] | None = None,
                       output_format: str | None = None, template_id: str | None = None,
                       template_version: str | None = None,
                       expires_at: datetime | None = None) -> Artifact: ...

    @abstractmethod
    async def get(self, artifact_id: str) -> Artifact | None: ...

    @abstractmethod
    async def path_for(self, artifact_id: str) -> Path | None: ...

    @abstractmethod
    async def list(self, *, run_id: str | None = None) -> list[Artifact]: ...


class BaseArtifactStore(ArtifactStore):
    """Shared write sequence; subclasses only decide where the record lives."""

    def __init__(self, files: WorkspaceArtifactFiles) -> None:
        self._files = files

    async def register(self, *, run_id: str, source_path: str, name: str | None = None,
                       artifact_type: str = "file", media_type: str | None = None,
                       metadata: dict[str, object] | None = None,
                       output_format: str | None = None, template_id: str | None = None,
                       template_version: str | None = None,
                       expires_at: datetime | None = None) -> Artifact:
        run_id = validated_run_id(run_id)
        source = self._files.validate_source(source_path)
        filename = validated_filename(name or source.name)
        artifact_id = str(uuid4())
        key = storage_key(run_id=run_id, artifact_id=artifact_id, filename=filename)

        pending = Artifact(
            id=artifact_id, name=filename, relative_path=key, artifact_type=artifact_type.strip() or "file",
            media_type=media_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
            size=0, sha256="0" * 64, status=ArtifactStatus.PENDING, run_id=run_id,
            created_at=datetime.now(timezone.utc), output_format=output_format,
            template_id=template_id, template_version=template_version, expires_at=expires_at,
            metadata=dict(metadata or {}),
        )
        await self._record_pending(pending)
        try:
            written = self._files.write(key, source)
        except (OSError, ValueError) as error:
            self._files.discard(key)
            await self._record_failed(artifact_id)
            raise ValueError("Artifact bytes could not be written.") from error

        ready = pending.model_copy(update={
            "size": written.size, "sha256": written.sha256, "status": ArtifactStatus.READY,
        })
        await self._record_ready(ready)
        return ready

    @abstractmethod
    async def _record_pending(self, artifact: Artifact) -> None: ...

    @abstractmethod
    async def _record_ready(self, artifact: Artifact) -> None: ...

    @abstractmethod
    async def _record_failed(self, artifact_id: str) -> None: ...


class WorkspaceArtifactStore(BaseArtifactStore):
    """Keep records in this process; the files themselves live in the workspace.

    Suitable for tests and single-process development. Records are lost on
    restart, which is what ``PostgresArtifactStore`` exists to fix.
    """

    def __init__(self, workspace: Workspace, *, max_artifact_bytes: int = 65_536,
                 files: WorkspaceArtifactFiles | None = None) -> None:
        # The file provider is accepted as well as derived so that this store and
        # PostgresArtifactStore can be given the same one, and so a test can
        # supply a provider that fails on write.
        super().__init__(files or WorkspaceArtifactFiles(workspace, max_artifact_bytes=max_artifact_bytes))
        self._artifacts: dict[str, Artifact] = {}

    async def _record_pending(self, artifact: Artifact) -> None:
        self._artifacts[artifact.id] = artifact

    async def _record_ready(self, artifact: Artifact) -> None:
        self._artifacts[artifact.id] = artifact

    async def _record_failed(self, artifact_id: str) -> None:
        existing = self._artifacts.get(artifact_id)
        if existing is not None:
            self._artifacts[artifact_id] = existing.model_copy(update={"status": ArtifactStatus.FAILED})

    async def get(self, artifact_id: str) -> Artifact | None:
        try:
            artifact = self._artifacts.get(validated_artifact_id(artifact_id))
        except ValueError:
            return None
        return artifact if artifact and artifact.status is ArtifactStatus.READY else None

    async def path_for(self, artifact_id: str) -> Path | None:
        artifact = await self.get(artifact_id)
        return self._files.path(artifact.relative_path) if artifact else None

    async def list(self, *, run_id: str | None = None) -> list[Artifact]:
        items = [item for item in self._artifacts.values() if item.status is ArtifactStatus.READY]
        if run_id is not None:
            items = [item for item in items if item.run_id == run_id]
        return sorted(items, key=lambda artifact: artifact.created_at, reverse=True)
