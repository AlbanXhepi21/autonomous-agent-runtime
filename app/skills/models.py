"""Typed metadata for filesystem-defined agent skills."""

from pydantic import BaseModel, ConfigDict, Field


class SkillMetadata(BaseModel):
    """Compact discovery information exposed before a skill is loaded."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    version: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    recommended_tools: list[str] = Field(default_factory=list)
