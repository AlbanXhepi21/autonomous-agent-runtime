"""Controlled argv-only subprocess execution rooted in the agent workspace."""

import asyncio
import os
import shutil
import signal
from collections.abc import Sequence
from time import perf_counter

from app.environment.models import CommandResult
from app.environment.policy import CommandPolicy, CommandPolicyError
from app.environment.workspace import Workspace, WorkspaceError


class CommandExecutor:
    """Run a small allowlist of non-interactive development commands safely."""

    def __init__(
        self,
        workspace: Workspace,
        *,
        allowed_commands: Sequence[str] = ("pytest",),
        timeout_seconds: float = 15,
        max_output_bytes: int = 16_384,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if max_output_bytes < 1:
            raise ValueError("max_output_bytes must be at least 1")
        self._workspace = workspace
        self._policy = CommandPolicy(frozenset(allowed_commands))
        # Resolve approved names once under runtime control. The model can only
        # choose a key from this mapping, never an executable path.
        self._executables = {
            name: executable
            for name in self._policy.allowed_commands
            if (executable := shutil.which(name)) is not None
        }
        self._timeout_seconds = timeout_seconds
        self._max_output_bytes = max_output_bytes

    @property
    def max_output_bytes(self) -> int:
        return self._max_output_bytes

    @property
    def allowed_commands(self) -> frozenset[str]:
        return self._policy.allowed_commands

    async def execute(
        self,
        command: str,
        args: Sequence[str] | None = None,
        *,
        working_directory: str | None = None,
    ) -> CommandResult:
        """Execute one allowlisted argv command and return a bounded result."""

        started_at = perf_counter()
        argv_args = list(args or [])
        try:
            self._policy.validate(command, argv_args)
            executable = self._executables.get(command)
            if executable is None:
                raise CommandPolicyError(f"Allowed command is unavailable: {command}.")
            directory = self._workspace.resolve(working_directory or ".")
            if not directory.is_dir():
                raise CommandPolicyError("Working directory does not exist in the workspace.")
        except (CommandPolicyError, WorkspaceError) as error:
            return self._result(False, started_at, denied=True, error=str(error))

        try:
            process = await asyncio.create_subprocess_exec(
                executable,
                *argv_args,
                cwd=str(directory),
                env=self._safe_environment(),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
        except OSError:
            return self._result(False, started_at, error="Command could not be started.")

        stdout_task = asyncio.create_task(self._capture_output(process.stdout))
        stderr_task = asyncio.create_task(self._capture_output(process.stderr))
        timed_out = False
        try:
            await asyncio.wait_for(process.wait(), timeout=self._timeout_seconds)
        except TimeoutError:
            timed_out = True
            await self._terminate(process)
        finally:
            stdout, stdout_truncated = await stdout_task
            stderr, stderr_truncated = await stderr_task

        if timed_out:
            return self._result(
                False, started_at, stdout=stdout, stderr=stderr,
                stdout_truncated=stdout_truncated, stderr_truncated=stderr_truncated,
                timed_out=True, error="Command timed out.",
            )
        return self._result(
            process.returncode == 0,
            started_at,
            stdout=stdout,
            stderr=stderr,
            return_code=process.returncode,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            error=None if process.returncode == 0 else "Command exited with a non-zero status.",
        )

    async def _capture_output(
        self, stream: asyncio.StreamReader | None,
    ) -> tuple[str, bool]:
        if stream is None:
            return "", False
        chunks: list[bytes] = []
        retained = 0
        truncated = False
        while chunk := await stream.read(4_096):
            remaining = self._max_output_bytes - retained
            if remaining > 0:
                chunks.append(chunk[:remaining])
                retained += min(len(chunk), remaining)
            if len(chunk) > remaining:
                truncated = True
        return b"".join(chunks).decode("utf-8", errors="replace"), truncated

    async def _terminate(self, process: asyncio.subprocess.Process) -> None:
        if process.returncode is not None:
            return
        if os.name == "posix" and process.pid is not None:
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=1)
        except TimeoutError:
            if os.name == "posix" and process.pid is not None:
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            await process.wait()

    @staticmethod
    def _safe_environment() -> dict[str, str]:
        """Use a fixed minimal environment; never forward host secrets."""

        return {
            "PATH": os.defpath,
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUNBUFFERED": "1",
        }

    @staticmethod
    def _result(
        success: bool,
        started_at: float,
        *,
        stdout: str = "",
        stderr: str = "",
        return_code: int | None = None,
        stdout_truncated: bool = False,
        stderr_truncated: bool = False,
        timed_out: bool = False,
        denied: bool = False,
        error: str | None = None,
    ) -> CommandResult:
        return CommandResult(
            success=success,
            stdout=stdout,
            stderr=stderr,
            return_code=return_code,
            duration_ms=round((perf_counter() - started_at) * 1_000),
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            timed_out=timed_out,
            denied=denied,
            error=error,
        )
