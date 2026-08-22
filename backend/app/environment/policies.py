"""Canonical path policy shared by all workspace filesystem operations."""

import ast
from pathlib import Path


class PythonExecutionPolicyError(ValueError):
    """Python source that exceeds restricted local execution policy."""


class PythonExecutionPolicy:
    """Apply source-size and explicit-import checks before process creation."""

    def __init__(self, allowed_imports: frozenset[str], max_code_bytes: int) -> None:
        if max_code_bytes < 1:
            raise ValueError("max_code_bytes must be at least 1")
        self._allowed_imports = allowed_imports
        self._max_code_bytes = max_code_bytes

    @property
    def allowed_imports(self) -> frozenset[str]:
        return self._allowed_imports

    def validate(self, code: str) -> None:
        if not isinstance(code, str):
            raise PythonExecutionPolicyError("Python code must be text.")
        if len(code.encode("utf-8")) > self._max_code_bytes:
            raise PythonExecutionPolicyError("Python code exceeds the configured size limit.")
        try:
            tree = ast.parse(code, mode="exec")
        except SyntaxError as error:
            raise PythonExecutionPolicyError("Python source is invalid.") from error
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    raise PythonExecutionPolicyError("Relative imports are not allowed.")
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if name.split(".", 1)[0] not in self._allowed_imports:
                    raise PythonExecutionPolicyError(f"Python import is not allowed: {name}.")


class CommandPolicyError(ValueError):
    """A command request that violates the conservative runtime policy."""


class CommandPolicy:
    """Validate executable names and argv values before process creation."""

    _SHELL_CONTROL_TOKENS = (";", "&&", "||", "$(", ">", "<", "`", "\n", "\r")

    def __init__(self, allowed_commands: frozenset[str]) -> None:
        if not allowed_commands:
            raise ValueError("At least one command must be allowlisted.")
        self._allowed_commands = allowed_commands

    @property
    def allowed_commands(self) -> frozenset[str]:
        return self._allowed_commands

    def validate(self, command: str, args: list[str]) -> None:
        if not isinstance(command, str) or not command.strip():
            raise CommandPolicyError("A non-empty command is required.")
        if command != command.strip() or "/" in command or "\\" in command:
            raise CommandPolicyError("Command must be an allowlisted executable name.")
        if command not in self._allowed_commands:
            raise CommandPolicyError(f"Command is not allowed: {command}.")
        for argument in args:
            if not isinstance(argument, str):
                raise CommandPolicyError("Command arguments must be strings.")
            if any(token in argument for token in self._SHELL_CONTROL_TOKENS):
                raise CommandPolicyError("Command arguments may not contain shell control syntax.")


class WorkspacePathPolicy:
    """Resolve only relative paths whose canonical target remains under one root."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve(strict=False)

    @property
    def root(self) -> Path:
        return self._root

    def resolve(self, relative_path: str) -> Path:
        """Return a canonical in-workspace target or reject the request."""

        candidate = Path(relative_path)
        if candidate.is_absolute():
            raise ValueError("Workspace paths must be relative.")
        resolved = (self._root / candidate).resolve(strict=False)
        try:
            resolved.relative_to(self._root)
        except ValueError as error:
            raise ValueError("Path is outside the workspace.") from error
        return resolved
