"""Replaceable artifact storage rooted in the configured Workspace."""

import mimetypes
import shutil
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app.artifacts.contracts import Artifact
from app.environment.workspace import Workspace, WorkspaceError
from app.security.credentials import contains_secret_material

_SENSITIVE_ARTIFACT_NAMES = frozenset({".env", ".env.local", ".env.production", "id_rsa", "id_ed25519", "credentials", "credentials.json"})


class ArtifactStore(ABC):
    """Persist and retrieve metadata-backed artifacts without exposing raw paths."""

    @abstractmethod
    def register(self, *, run_id: str, source_path: str, name: str | None = None,
                 artifact_type: str = "file", media_type: str | None = None,
                 metadata: dict[str, object] | None = None) -> Artifact: ...

    @abstractmethod
    def get(self, artifact_id: str) -> Artifact | None: ...

    @abstractmethod
    def path_for(self, artifact_id: str) -> Path | None: ...

    @abstractmethod
    def list(self, *, run_id: str | None = None) -> list[Artifact]: ...


class WorkspaceArtifactStore(ArtifactStore):
    """Copy explicit workspace files into ``artifacts/<run_id>/`` for development."""

    def __init__(self, workspace: Workspace, *, max_artifact_bytes: int = 65_536) -> None:
        if max_artifact_bytes < 1:
            raise ValueError("max_artifact_bytes must be at least 1")
        self._workspace = workspace
        self._artifacts: dict[str, Artifact] = {}
        self._max_artifact_bytes = max_artifact_bytes

    def register(self, *, run_id: str, source_path: str, name: str | None = None,
                 artifact_type: str = "file", media_type: str | None = None,
                 metadata: dict[str, object] | None = None) -> Artifact:
        if not run_id.strip() or Path(run_id).name != run_id or run_id in {".", ".."} or "\0" in run_id:
            raise ValueError("A run ID is required to register an artifact.")
        try:
            source = self._workspace.resolve(source_path)
        except WorkspaceError as error:
            raise ValueError(str(error)) from error
        if not source.is_file():
            raise ValueError("Artifact source must be a workspace file.")
        if source.name.lower() in _SENSITIVE_ARTIFACT_NAMES or source.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
            raise ValueError("Sensitive credential files cannot be registered as artifacts.")
        if source.stat().st_size > self._max_artifact_bytes:
            raise ValueError("Artifact source exceeds the configured size limit.")
        try:
            if contains_secret_material(source.read_text(encoding="utf-8")):
                raise ValueError("Files containing credential material cannot be registered as artifacts.")
        except UnicodeDecodeError:
            pass
        artifact_name = name or source.name
        if Path(artifact_name).name != artifact_name or artifact_name in {"", ".", ".."} or "\0" in artifact_name:
            raise ValueError("Artifact name must be a simple filename.")
        artifact_id = str(uuid4())
        destination_directory = self._workspace.root / "artifacts" / run_id
        destination_directory.mkdir(parents=True, exist_ok=True)
        destination = destination_directory / f"{artifact_id}-{artifact_name}"
        destination = destination.resolve(strict=False)
        try:
            destination.relative_to(self._workspace.root / "artifacts")
        except ValueError as error:
            raise ValueError("Artifact destination is outside the artifact area.") from error
        shutil.copyfile(source, destination)
        artifact = Artifact(
            id=artifact_id,
            name=artifact_name,
            relative_path=destination.relative_to(self._workspace.root).as_posix(),
            artifact_type=artifact_type.strip() or "file",
            media_type=media_type or mimetypes.guess_type(artifact_name)[0] or "application/octet-stream",
            size=destination.stat().st_size,
            run_id=run_id,
            created_at=datetime.now(timezone.utc),
            metadata=dict(metadata or {}),
        )
        self._artifacts[artifact.id] = artifact
        return artifact

    def get(self, artifact_id: str) -> Artifact | None:
        try:
            return self._artifacts.get(self._validated_id(artifact_id))
        except ValueError:
            return None

    def path_for(self, artifact_id: str) -> Path | None:
        artifact = self.get(artifact_id)
        if artifact is None:
            return None
        try:
            path = self._workspace.resolve(artifact.relative_path)
            path.relative_to(self._workspace.root / "artifacts")
        except (WorkspaceError, ValueError):
            return None
        return path if path.is_file() else None

    def list(self, *, run_id: str | None = None) -> list[Artifact]:
        items = self._artifacts.values()
        if run_id is not None:
            items = (artifact for artifact in items if artifact.run_id == run_id)
        return sorted(items, key=lambda artifact: artifact.created_at, reverse=True)

    @staticmethod
    def _validated_id(artifact_id: str) -> str:
        try:
            return str(UUID(artifact_id))
        except (ValueError, TypeError) as error:
            raise ValueError("Invalid artifact ID.") from error
