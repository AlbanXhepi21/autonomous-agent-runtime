"""Restricted local Python execution in a disposable child-process directory.

This is intentionally not a hostile-code sandbox. It removes direct filesystem and
network-oriented imports from the supported interface, but process isolation and
import filtering alone cannot provide complete operating-system isolation.
"""

import asyncio
import os
import shutil
import signal
import sys
import tempfile
import json
from collections.abc import Sequence
from pathlib import Path
from time import perf_counter

from app.environment.models import PythonExecutionResult
from app.environment.policy import PythonExecutionPolicy, PythonExecutionPolicyError
from app.environment.workspace import Workspace, WorkspaceError

DEFAULT_PYTHON_IMPORTS = frozenset({"math", "statistics", "json", "datetime", "collections"})

_BOOTSTRAP = '''\
import builtins
import importlib
import sys
import json

ALLOWED_IMPORTS = frozenset({allowed_imports!r})

def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level or name.split('.', 1)[0] not in ALLOWED_IMPORTS:
        raise ImportError("This import is not allowed in restricted local execution.")
    module = importlib.import_module(name)
    return module if fromlist else importlib.import_module(name.split('.', 1)[0])

SAFE_BUILTINS = {{
    "__build_class__": builtins.__build_class__, "__import__": restricted_import,
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
    "enumerate": enumerate, "filter": filter, "float": float, "frozenset": frozenset,
    "int": int, "isinstance": isinstance, "len": len, "list": list, "map": map,
    "max": max, "min": min, "object": object, "print": print, "range": range,
    "reversed": reversed, "round": round, "set": set, "sorted": sorted, "str": str,
    "sum": sum, "tuple": tuple, "zip": zip, "Exception": Exception,
    "ValueError": ValueError, "TypeError": TypeError, "RuntimeError": RuntimeError,
}}

try:
    analytics_data = json.loads(builtins.open("dataset.json", "r", encoding="utf-8").read())
    source = builtins.open("payload.py", "r", encoding="utf-8").read()
    exec(compile(source, "payload.py", "exec"), {{"__builtins__": SAFE_BUILTINS, "__name__": "__main__", "analytics_data": analytics_data}})
except BaseException as error:
    print(f"Python execution failed: {{type(error).__name__}}: {{error}}", file=sys.stderr)
    raise SystemExit(1)
'''


def _child_error(stderr: str) -> str:
    """Return one safe, bounded sandbox diagnostic for agent recovery."""

    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    return (lines[-1] if lines else "Python execution failed.")[:500]


class PythonExecutor:
    """Execute policy-approved code only in a separate disposable Python process."""

    def __init__(
        self,
        workspace: Workspace,
        *,
        allowed_imports: Sequence[str] = tuple(DEFAULT_PYTHON_IMPORTS),
        timeout_seconds: float = 10,
        max_code_bytes: int = 16_384,
        max_output_bytes: int = 16_384,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if max_output_bytes < 1:
            raise ValueError("max_output_bytes must be at least 1")
        self._workspace = workspace
        self._policy = PythonExecutionPolicy(frozenset(allowed_imports), max_code_bytes)
        self._timeout_seconds = timeout_seconds
        self._max_output_bytes = max_output_bytes

    @property
    def max_output_bytes(self) -> int:
        return self._max_output_bytes

    @property
    def allowed_imports(self) -> frozenset[str]:
        return self._policy.allowed_imports

    @property
    def workspace(self) -> Workspace:
        """Expose the trusted workspace only to runtime-owned adapters."""

        return self._workspace

    async def execute(
        self, code: str, *, dataset: dict[str, object] | None = None,
        output_directory: Path | None = None,
    ) -> PythonExecutionResult:
        """Run source in a private temp directory and remove it on every outcome."""

        started_at = perf_counter()
        try:
            self._policy.validate(code)
        except PythonExecutionPolicyError as error:
            return self._result(False, started_at, error=str(error))
        try:
            workspace_root = self._workspace.resolve(".")
            workspace_root.mkdir(parents=True, exist_ok=True)
            run_directory = Path(tempfile.mkdtemp(prefix="python-exec-", dir=workspace_root))
        except (WorkspaceError, OSError):
            return self._result(False, started_at, error="Python execution directory could not be created.")

        try:
            (run_directory / "payload.py").write_text(code, encoding="utf-8")
            (run_directory / "dataset.json").write_text(json.dumps(dataset or {}), encoding="utf-8")
            (run_directory / "bootstrap.py").write_text(
                _BOOTSTRAP.format(allowed_imports=sorted(self.allowed_imports)), encoding="utf-8"
            )
            result = await self._run_child(run_directory, started_at)
            if output_directory is not None and result.success:
                result.generated_files = self._collect_charts(run_directory, output_directory)
            return result
        except OSError:
            return self._result(False, started_at, error="Python execution could not be prepared.")
        finally:
            shutil.rmtree(run_directory, ignore_errors=True)

    async def _run_child(self, run_directory: Path, started_at: float) -> PythonExecutionResult:
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-I", "bootstrap.py",
                cwd=str(run_directory), env=self._safe_environment(),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
        except OSError:
            return self._result(False, started_at, error="Python execution process could not be started.")
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
                timed_out=True, error="Python execution timed out.",
            )
        return self._result(
            process.returncode == 0, started_at, stdout=stdout, stderr=stderr,
            return_code=process.returncode, stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            # The child has no credentials or inherited environment. Retain a
            # bounded diagnostic so the agent can correct safe Python mistakes
            # instead of blindly repeating the same failing action.
            error=None if process.returncode == 0 else _child_error(stderr),
        )

    async def _capture_output(self, stream: asyncio.StreamReader | None) -> tuple[str, bool]:
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
        if process.returncode is None:
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
        return {"PATH": os.defpath, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1", "MPLCONFIGDIR": "."}

    def _collect_charts(self, run_directory: Path, output_directory: Path) -> list[str]:
        """Copy only bounded PNG charts into a runtime-owned workspace directory."""

        try:
            output_directory.resolve(strict=False).relative_to(self._workspace.root)
            output_directory.mkdir(parents=True, exist_ok=True)
        except (OSError, ValueError):
            return []
        results: list[str] = []
        for index, source in enumerate(sorted(run_directory.glob("*.png")), start=1):
            if index > 5 or source.stat().st_size > self._workspace.limits.max_file_write_bytes:
                break
            destination = output_directory / f"chart-{index}.png"
            try:
                shutil.copyfile(source, destination)
                results.append(destination.relative_to(self._workspace.root).as_posix())
            except OSError:
                continue
        return results

    @staticmethod
    def _result(
        success: bool, started_at: float, *, stdout: str = "", stderr: str = "",
        return_code: int | None = None, stdout_truncated: bool = False,
        stderr_truncated: bool = False, timed_out: bool = False, error: str | None = None,
    ) -> PythonExecutionResult:
        return PythonExecutionResult(
            success=success, stdout=stdout, stderr=stderr, return_code=return_code,
            duration_ms=round((perf_counter() - started_at) * 1_000),
            stdout_truncated=stdout_truncated, stderr_truncated=stderr_truncated,
            timed_out=timed_out, error=error,
        )
