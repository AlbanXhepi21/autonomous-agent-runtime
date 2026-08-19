"""Models shared by the tool execution layer."""

from typing import Any

from pydantic import BaseModel, Field
from app.security.models import ContentTrust


class ToolResult(BaseModel):
    """A safe, structured outcome of one tool invocation."""

    success: bool
    output: Any | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    trust: ContentTrust = ContentTrust.TOOL_OUTPUT
    source_type: str | None = None
    source_identifier: str | None = None
