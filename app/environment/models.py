"""Configuration models for a controlled agent workspace."""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field


@dataclass(frozen=True, slots=True)
class WorkspaceLimits:
    """Hard bounds applied to all workspace filesystem operations."""

    max_file_read_bytes: int = 65_536
    max_file_write_bytes: int = 65_536
    max_list_files: int = 100

    def __post_init__(self) -> None:
        for name, value in (
            ("max_file_read_bytes", self.max_file_read_bytes),
            ("max_file_write_bytes", self.max_file_write_bytes),
            ("max_list_files", self.max_list_files),
        ):
            if value < 1:
                raise ValueError(f"{name} must be at least 1")


class CommandResult(BaseModel):
    """A bounded, serializable outcome from one argv-based command invocation."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int | None = None
    duration_ms: int = Field(ge=0)
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    timed_out: bool = False
    denied: bool = False
    error: str | None = None


class PythonExecutionResult(BaseModel):
    """A bounded outcome from one restricted local Python child process."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int | None = None
    duration_ms: int = Field(ge=0)
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    timed_out: bool = False
    error: str | None = None
