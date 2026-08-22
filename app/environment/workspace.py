"""Safe filesystem operations rooted in one configured workspace directory."""

import logging
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.core.logging import log_event
from app.environment.contracts import WorkspaceLimits
from app.environment.policies import WorkspacePathPolicy


class WorkspaceError(ValueError):
    """A safe filesystem-policy failure suitable for a tool observation."""


class Workspace:
    """Resolve and operate on files only through a canonical workspace root."""

    def __init__(self, root: Path, limits: WorkspaceLimits | None = None) -> None:
        self._policy = WorkspacePathPolicy(root)
        self._limits = limits or WorkspaceLimits()
        self._modified_files: set[str] = set()
        self._logger = logging.getLogger(__name__)
        log_event(self._logger, logging.INFO, "workspace_initialized", root="configured")

    @property
    def limits(self) -> WorkspaceLimits:
        return self._limits

    @property
    def root(self) -> Path:
        """Return the canonical root for trusted environment components."""

        return self._policy.root

    def changed_files(self) -> list[str]:
        """Return paths changed through this workspace instance during its lifetime."""

        return sorted(self._modified_files)

    def resolve(self, relative_path: str) -> Path:
        """Resolve one caller-provided relative path through the shared policy."""

        if not isinstance(relative_path, str) or not relative_path.strip():
            raise WorkspaceError("A non-empty workspace path is required.")
        try:
            return self._policy.resolve(relative_path)
        except ValueError as error:
            raise WorkspaceError(str(error)) from error

    def list_files(self, relative_path: str = ".", *, recursive: bool = False) -> list[str]:
        directory = self.resolve(relative_path)
        if not directory.is_dir():
            raise WorkspaceError("Workspace directory does not exist.")
        iterator = directory.rglob("*") if recursive else directory.iterdir()
        results: list[str] = []
        for entry in sorted(iterator, key=lambda item: item.as_posix()):
            try:
                resolved = self.resolve(entry.relative_to(self._policy.root).as_posix())
            except WorkspaceError:
                continue
            if resolved.is_dir() and entry.is_symlink():
                continue
            results.append(resolved.relative_to(self._policy.root).as_posix() + ("/" if resolved.is_dir() else ""))
            if len(results) >= self._limits.max_list_files:
                break
        return results

    def read_text(self, relative_path: str) -> str:
        path = self.resolve(relative_path)
        if not path.is_file():
            raise WorkspaceError("Workspace file does not exist.")
        try:
            size = path.stat().st_size
        except OSError as error:
            raise WorkspaceError("Workspace file could not be read.") from error
        if size > self._limits.max_file_read_bytes:
            raise WorkspaceError("Workspace file exceeds the read size limit.")
        try:
            content = path.read_bytes()
        except OSError as error:
            raise WorkspaceError("Workspace file could not be read.") from error
        if b"\0" in content:
            raise WorkspaceError("Workspace file appears to be binary.")
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise WorkspaceError("Workspace file is not valid UTF-8 text.") from error

    def write_text(self, relative_path: str, content: str, *, create_parents: bool = False) -> None:
        if not isinstance(content, str):
            raise WorkspaceError("Workspace file content must be text.")
        encoded = content.encode("utf-8")
        if len(encoded) > self._limits.max_file_write_bytes:
            raise WorkspaceError("Workspace content exceeds the write size limit.")
        path = self.resolve(relative_path)
        parent = path.parent
        if not parent.exists():
            if not create_parents:
                raise WorkspaceError("Parent directory does not exist.")
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except OSError as error:
                raise WorkspaceError("Parent directory could not be created.") from error
        if not parent.is_dir():
            raise WorkspaceError("Parent path is not a directory.")
        # Resolve again after directory creation to catch symlink changes or traversal.
        path = self.resolve(relative_path)
        try:
            with NamedTemporaryFile("wb", dir=path.parent, delete=False) as temporary:
                temporary.write(encoded)
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, path)
            self._modified_files.add(path.relative_to(self._policy.root).as_posix())
        except OSError as error:
            try:
                temporary_path.unlink(missing_ok=True)
            except UnboundLocalError:
                pass
            raise WorkspaceError("Workspace file could not be written.") from error
