"""Typed contracts for trusted runtime query handling."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SQLQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sql: str = Field(min_length=1, max_length=20_000)
    purpose: str | None = Field(default=None, max_length=1_000)


class SQLColumn(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    data_type: str | None = None


class SQLValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    valid: bool
    reason: str
    statement_type: str | None = None
    referenced_tables: list[str] = Field(default_factory=list)
    potential_issues: list[str] = Field(default_factory=list)


class SQLQueryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    columns: list[SQLColumn]
    rows: list[list[Any]]
    row_count: int = Field(ge=0)
    truncated: bool = False
    execution_ms: int = Field(ge=0)
    referenced_tables: list[str] = Field(default_factory=list)
