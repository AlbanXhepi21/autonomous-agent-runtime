"""Models shared by the tool execution layer."""

from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """A safe, structured outcome of one tool invocation."""

    success: bool
    output: Any | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
