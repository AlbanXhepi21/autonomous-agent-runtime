"""The binary side of artifact storage, kept apart from the record of it.

Both the in-process and the PostgreSQL registries write bytes the same way and
differ only in where the record lives. Separating the two means the validation
that decides whether a file may become an artifact exists once, and means a
future object-store provider replaces this class without touching either
registry.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from app.environment.workspace import Workspace, WorkspaceError
from app.security.credentials import contains_secret_material

#: Files that must never become downloadable, whatever a caller names them.
SENSITIVE_ARTIFACT_NAMES = frozenset(
    {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519", "credentials", "credentials.json"}
)
SENSITIVE_ARTIFACT_SUFFIXES = frozenset({".pem", ".key", ".p12", ".pfx"})

#: Everything an artifact provider owns lives under this workspace directory.
ARTIFACT_AREA = "artifacts"

_DIGEST_CHUNK = 1024 * 1024


@dataclass(frozen=True, slots=True)
class StoredBytes:
    """What was actually written, as opposed to what was asked for."""

    size: int
    sha256: str


def storage_key(*, run_id: str, artifact_id: str, filename: str) -> str:
    """Build the provider-independent key a record stores.

    One directory per artifact rather than a shared directory with prefixed
    names, so a key ends in the filename the reader downloads.
    """

    return f"{ARTIFACT_AREA}/{run_id}/{artifact_id}/{filename}"


def digest_of(path: Path) -> StoredBytes:
    """Hash a file without holding it in memory."""

    digest = sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(_DIGEST_CHUNK):
            digest.update(chunk)
            size += len(chunk)
    return StoredBytes(size=size, sha256=digest.hexdigest())


class WorkspaceArtifactFiles:
    """Copy approved workspace files into the artifact area and resolve them back."""

    def __init__(self, workspace: Workspace, *, max_artifact_bytes: int) -> None:
        if max_artifact_bytes < 1:
            raise ValueError("max_artifact_bytes must be at least 1")
        self._workspace = workspace
        self._max_artifact_bytes = max_artifact_bytes

    def validate_source(self, source_path: str) -> Path:
        """Return the resolved source, or explain why it cannot become an artifact."""

        try:
            source = self._workspace.resolve(source_path)
        except WorkspaceError as error:
            raise ValueError(str(error)) from error
        if not source.is_file():
            raise ValueError("Artifact source must be a workspace file.")
        if source.name.lower() in SENSITIVE_ARTIFACT_NAMES or source.suffix.lower() in SENSITIVE_ARTIFACT_SUFFIXES:
            raise ValueError("Sensitive credential files cannot be registered as artifacts.")
        if source.stat().st_size > self._max_artifact_bytes:
            raise ValueError("Artifact source exceeds the configured size limit.")
        try:
            if contains_secret_material(source.read_text(encoding="utf-8")):
                raise ValueError("Files containing credential material cannot be registered as artifacts.")
        except UnicodeDecodeError:
            pass
        return source

    def write(self, key: str, source: Path) -> StoredBytes:
        """Copy the source to its key and report what landed there."""

        destination = self._destination(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        return digest_of(destination)

    def path(self, key: str) -> Path | None:
        """Resolve a key to a readable file, or None when it is not one."""

        try:
            destination = self._destination(key)
        except ValueError:
            return None
        return destination if destination.is_file() else None

    def discard(self, key: str) -> None:
        """Remove a partially written file; failure to clean up is not fatal."""

        try:
            destination = self._destination(key)
        except ValueError:
            return
        destination.unlink(missing_ok=True)

    def _destination(self, key: str) -> Path:
        """Resolve a key inside the artifact area, refusing anything that escapes it."""

        try:
            destination = self._workspace.resolve(key).resolve(strict=False)
            destination.relative_to((self._workspace.root / ARTIFACT_AREA).resolve(strict=False))
        except (WorkspaceError, ValueError) as error:
            raise ValueError("Artifact destination is outside the artifact area.") from error
        return destination
