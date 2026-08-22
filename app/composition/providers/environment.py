"""The filesystem, command and Python execution boundaries agents act within."""

from pathlib import Path

from app.composition.providers.settings import get_settings
from app.config import Settings
from app.environment import CommandExecutor, PythonExecutor, Workspace, WorkspaceLimits
from app.environment.repository import Repository


def get_workspace(settings: Settings | None = None) -> Workspace:
    """Build the configured filesystem boundary without exposing host paths to agents."""

    settings = settings or get_settings()
    return Workspace(
        Path(settings.agent_workspace_root),
        WorkspaceLimits(
            max_file_read_bytes=settings.max_file_read_bytes,
            max_file_write_bytes=settings.max_file_write_bytes,
            max_list_files=settings.max_list_files,
        ),
    )


def get_command_executor(workspace: Workspace, settings: Settings | None = None) -> CommandExecutor:
    """Build the argv-only command boundary using runtime-owned configuration."""

    settings = settings or get_settings()
    return CommandExecutor(
        workspace,
        allowed_commands=settings.command_allowlist_items,
        timeout_seconds=settings.command_timeout_seconds,
        max_output_bytes=settings.max_command_output_bytes,
    )


def get_python_executor(workspace: Workspace, settings: Settings | None = None) -> PythonExecutor:
    """Build the restricted child-process Python executor from runtime settings."""

    settings = settings or get_settings()
    return PythonExecutor(
        workspace,
        allowed_imports=settings.python_exec_allowed_import_items,
        timeout_seconds=settings.python_exec_timeout_seconds,
        max_code_bytes=settings.max_python_code_bytes,
        max_output_bytes=settings.max_python_output_bytes,
    )


def get_repository(workspace: Workspace) -> Repository:
    """Build the bounded repository inspection layer over the shared workspace."""

    return Repository(workspace)
