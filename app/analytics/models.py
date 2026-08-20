"""Sanitized metadata contracts exposed to the agent runtime."""

from pydantic import BaseModel, ConfigDict, Field


class DatabaseTable(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)
    name: str = Field(min_length=1)
    schema_name: str = Field(min_length=1, alias="schema", serialization_alias="schema")


class DatabaseColumn(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    nullable: bool
    primary_key: bool = False
    foreign_key_target: str | None = None


class ForeignKeyRelationship(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_table: str = Field(min_length=1)
    source_column: str = Field(min_length=1)
    target_table: str = Field(min_length=1)
    target_column: str = Field(min_length=1)
    source_schema: str = Field(min_length=1)
    target_schema: str = Field(min_length=1)


class TableDescription(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)
    name: str
    schema_name: str = Field(alias="schema", serialization_alias="schema")
    columns: list[DatabaseColumn]
    primary_key: list[str] = Field(default_factory=list)
    foreign_keys: list[ForeignKeyRelationship] = Field(default_factory=list)
    unique_constraints: list[list[str]] = Field(default_factory=list)


class DatabaseSchemaSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schemas: list[str]
    tables: list[DatabaseTable]
