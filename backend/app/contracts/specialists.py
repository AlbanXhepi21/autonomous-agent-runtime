"""Typed definitions for filesystem-defined specialist agents."""

from pydantic import BaseModel, ConfigDict, Field


class AgentRuntimeOverrides(BaseModel):
    """Optional limits to apply if this definition is run in a future version."""

    model_config = ConfigDict(extra="forbid")

    max_iterations: int | None = Field(default=None, ge=1)


class AgentMetadata(BaseModel):
    """Compact discovery information for an available specialist agent."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    version: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_skills: list[str] = Field(default_factory=list)
    runtime_overrides: AgentRuntimeOverrides = Field(default_factory=AgentRuntimeOverrides)


class AgentDefinition(AgentMetadata):
    """A complete specialist definition, separate from mutable run state."""

    instructions: str = Field(min_length=1)
