"""Bounded repository inspection built on the workspace path boundary."""

import asyncio
import os
import shutil
from collections.abc import Iterator
from pathlib import Path

from app.environment.workspace import Workspace, WorkspaceError

DEFAULT_IGNORED_DIRECTORIES = frozenset({".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"})


class RepositoryError(ValueError):
    """A safe repository inspection failure."""


class Repository:
    """Provide compact, source-oriented repository views without bypassing Workspace."""

    def __init__(
        self, workspace: Workspace, *, ignored_directories: frozenset[str] = DEFAULT_IGNORED_DIRECTORIES,
        max_entries: int = 200, max_search_results: int = 50, max_files_scanned: int = 500,
    ) -> None:
        if max_entries < 1 or max_search_results < 1 or max_files_scanned < 1:
            raise ValueError("Repository limits must be at least 1")
        self._workspace = workspace
        self._ignored_directories = ignored_directories
        self._max_entries = max_entries
        self._max_search_results = max_search_results
        self._max_files_scanned = max_files_scanned

    def tree(self, *, max_depth: int = 3, max_entries: int | None = None) -> list[dict[str, str]]:
        if max_depth < 1:
            raise RepositoryError("max_depth must be at least 1.")
        limit = min(max_entries or self._max_entries, self._max_entries)
        if limit < 1:
            raise RepositoryError("max_entries must be at least 1.")
        entries: list[dict[str, str]] = []
        for path in self._iter_paths():
            relative = path.relative_to(self._workspace.root)
            if len(relative.parts) > max_depth:
                continue
            entries.append({"path": relative.as_posix(), "type": "directory" if path.is_dir() else "file"})
            if len(entries) >= limit:
                break
        return entries

    def search(self, *, path_query: str | None = None, text_query: str | None = None,
               max_results: int | None = None) -> list[dict[str, object]]:
        if not path_query and not text_query:
            raise RepositoryError("Provide a path_query or text_query.")
        limit = min(max_results or self._max_search_results, self._max_search_results)
        if limit < 1:
            raise RepositoryError("max_results must be at least 1.")
        normalized_path = path_query.lower() if path_query else None
        results: list[dict[str, object]] = []
        for scanned, path in enumerate(self._iter_paths(files_only=True), start=1):
            if scanned > self._max_files_scanned:
                break
            relative = path.relative_to(self._workspace.root).as_posix()
            if normalized_path and normalized_path not in relative.lower():
                continue
            if text_query:
                try:
                    content = self._workspace.read_text(relative)
                except WorkspaceError:
                    continue
                occurrences = content.count(text_query)
                if not occurrences:
                    continue
            else:
                occurrences = 0
            results.append({"path": relative, "text_matches": occurrences})
            if len(results) >= limit:
                break
        return results

    def changed_files(self) -> list[str]:
        """Report files modified through the controlled Workspace write path."""

        return self._workspace.changed_files()

    async def git_inspect(self, operation: str, *, max_output_bytes: int = 16_384) -> dict[str, object]:
        """Run a fixed read-only Git inspection command when Git is available."""

        commands = {
            "status": ("status", "--short"),
            "diff": ("diff", "--stat"),
            "log": ("log", "--oneline", "-n", "20"),
        }
        if operation not in commands:
            raise RepositoryError("Git operation is not allowed.")
        executable = shutil.which("git")
        if executable is None:
            return {"success": False, "stdout": "", "stderr": "", "return_code": None, "error": "Git is unavailable."}
        try:
            process = await asyncio.create_subprocess_exec(
                executable, *commands[operation], cwd=str(self._workspace.root),
                env={"PATH": os.defpath}, stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5)
            except TimeoutError:
                process.terminate()
                await process.wait()
                return {"success": False, "stdout": "", "stderr": "", "return_code": None, "error": "Git inspection timed out."}
        except OSError:
            return {"success": False, "stdout": "", "stderr": "", "return_code": None, "error": "Git inspection could not start."}
        return {
            "success": process.returncode == 0,
            "stdout": stdout[:max_output_bytes].decode("utf-8", errors="replace"),
            "stderr": stderr[:max_output_bytes].decode("utf-8", errors="replace"),
            "return_code": process.returncode,
            "stdout_truncated": len(stdout) > max_output_bytes,
            "stderr_truncated": len(stderr) > max_output_bytes,
            "error": None if process.returncode == 0 else "Git inspection failed.",
        }

    def _iter_paths(self, *, files_only: bool = False) -> Iterator[Path]:
        root = self._workspace.root
        if not root.is_dir():
            raise RepositoryError("Repository workspace does not exist.")
        for directory, directories, files in os.walk(root, topdown=True, followlinks=False):
            directories[:] = sorted(name for name in directories if name not in self._ignored_directories)
            current = Path(directory)
            if not files_only and current != root:
                try:
                    yield self._safe_path(current)
                except RepositoryError:
                    continue
            for filename in sorted(files):
                try:
                    yield self._safe_path(current / filename)
                except RepositoryError:
                    continue

    def _safe_path(self, path: Path) -> Path:
        try:
            resolved = path.resolve(strict=False)
            resolved.relative_to(self._workspace.root)
            return resolved
        except ValueError as error:
            raise RepositoryError("Repository path is outside the workspace.") from error
