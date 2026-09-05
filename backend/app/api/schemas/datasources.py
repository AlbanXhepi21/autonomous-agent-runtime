"""Stable, frontend-facing contracts for workspace data source onboarding.

Never carries a password: ``DataSourceCreateRequest`` accepts one on the way
in, but no response schema here has a field for it -- the same guarantee
``DataSourceConnection`` itself makes, kept at the API boundary too.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


_CONFIG_FIELDS = (
    "host", "port", "database", "username", "ssl_mode", "allowed_schemas",
    "statement_timeout_seconds", "connection_timeout_seconds", "max_result_rows", "max_result_bytes",
)


class DataSourceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2_000)
    engine: Literal["postgresql"] = "postgresql"
    environment: Literal["development", "staging", "production"] = "development"
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=5432, ge=1, le=65_535)
    database: str = Field(min_length=1, max_length=128)
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1_000)
    ssl_mode: Literal["require", "verify-ca", "verify-full"] = "require"
    allowed_schemas: list[str] = Field(min_length=1, max_length=20)
    statement_timeout_seconds: float = Field(default=15, gt=0, le=120)
    connection_timeout_seconds: float = Field(default=10, gt=0, le=60)
    source_timezone: str | None = Field(default=None, max_length=64)
    max_result_rows: int = Field(default=5_000, ge=1, le=50_000)
    max_result_bytes: int = Field(default=1_000_000, ge=1_024)


class DataSourceUpdateRequest(BaseModel):
    """Edit non-secret configuration. Never carries a password -- see
    ``DataSourceReplaceCredentialsRequest`` for that.

    ``name``/``description``/``environment`` may each be changed
    independently. The connection-detail fields (host, port, ...) form one
    unit: to change any of them, all must be supplied together, since they
    replace the stored configuration as a whole rather than patching one
    field in place.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2_000)
    environment: Literal["development", "staging", "production"] | None = None
    host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65_535)
    database: str | None = Field(default=None, min_length=1, max_length=128)
    username: str | None = Field(default=None, min_length=1, max_length=128)
    ssl_mode: Literal["require", "verify-ca", "verify-full"] | None = None
    allowed_schemas: list[str] | None = Field(default=None, min_length=1, max_length=20)
    statement_timeout_seconds: float | None = Field(default=None, gt=0, le=120)
    connection_timeout_seconds: float | None = Field(default=None, gt=0, le=60)
    source_timezone: str | None = Field(default=None, max_length=64)
    max_result_rows: int | None = Field(default=None, ge=1, le=50_000)
    max_result_bytes: int | None = Field(default=None, ge=1_024)

    @model_validator(mode="after")
    def _connection_fields_are_all_or_nothing(self) -> DataSourceUpdateRequest:
        present = [field for field in _CONFIG_FIELDS if getattr(self, field) is not None]
        if present and len(present) != len(_CONFIG_FIELDS):
            missing = sorted(set(_CONFIG_FIELDS) - set(present))
            raise ValueError(f"To change connection details, also supply: {', '.join(missing)}.")
        return self

    @property
    def has_connection_changes(self) -> bool:
        return self.host is not None


class DataSourceReplaceCredentialsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=1_000)


class DataSourceResponse(BaseModel):
    id: str
    workspace_id: UUID
    name: str
    description: str | None
    engine: str
    environment: str
    host: str
    port: int
    database: str
    username: str
    ssl_mode: str
    allowed_schemas: list[str]
    statement_timeout_seconds: float
    connection_timeout_seconds: float
    source_timezone: str | None
    max_result_rows: int
    max_result_bytes: int
    status: str
    health_status: str
    last_connection_at: datetime | None
    last_connection_error: str | None
    last_error_category: str | None
    last_successful_connection_at: datetime | None
    last_profiled_at: datetime | None
    created_by: str | None
    version: int
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DataSourceListResponse(BaseModel):
    items: list[DataSourceResponse]
    total: int
    limit: int
    offset: int


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str
    error_category: str | None
    server_version: str | None
    ssl_active: bool | None
    accessible_schemas: list[str]
    latency_ms: float | None
    tested_at: datetime


class ReadOnlyVerificationResponse(BaseModel):
    is_read_only: bool
    role_is_superuser: bool
    role_can_create_database: bool
    role_can_create_role: bool
    role_bypasses_row_level_security: bool
    message: str


class SchemaSummaryResponse(BaseModel):
    schemas: list[str]
    tables: list[dict]


class SelectTableRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_name: str = Field(min_length=1, max_length=128)
    technical_name: str = Field(min_length=1, max_length=128)
    business_name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2_000)
    grain: str | None = Field(default=None, max_length=500)
    freshness_column: str | None = Field(default=None, max_length=128)


class ColumnCorrectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technical_name: str = Field(min_length=1, max_length=128)
    data_type: str = Field(min_length=1, max_length=64)
    role: Literal["primary_key", "dimension", "measure", "time", "identifier", "other"] = "other"
    sensitivity: Literal[
        "public", "internal", "personal_data", "financial_data", "authentication_secret", "restricted",
    ] = "internal"
    excluded: bool = False
    example_values: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _sensitive_columns_never_carry_examples(self) -> ColumnCorrectionPayload:
        if self.sensitivity in {"personal_data", "financial_data", "authentication_secret", "restricted"} and self.example_values:
            raise ValueError(f"A {self.sensitivity} column must not carry sampled example values.")
        return self


class TableCorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2_000)
    grain: str | None = Field(default=None, max_length=500)
    freshness_column: str | None = Field(default=None, max_length=128)
    columns: list[ColumnCorrectionPayload] = Field(min_length=1)


class TableActiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    active: bool


class ApproveTableRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approved_by: str = Field(min_length=1, max_length=128)


class ColumnResponse(BaseModel):
    id: str
    technical_name: str
    data_type: str
    role: str
    sensitivity: str
    excluded: bool
    example_values: list[str]


class TableResponse(BaseModel):
    id: str
    data_source_id: str
    schema_name: str
    technical_name: str
    business_name: str
    description: str | None
    grain: str | None
    freshness_column: str | None
    active: bool
    approved_by: str | None
    approved_at: datetime | None
    columns: list[ColumnResponse]
    primary_key: list[str]
    dimensions: list[str]
    measures: list[str]
    time_columns: list[str]
    sensitive_columns: list[str]
    created_at: datetime
    updated_at: datetime


class TableListResponse(BaseModel):
    items: list[TableResponse]


class RelationshipApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approval_status: Literal["approved", "rejected"]
    approved_by: str | None = Field(default=None, max_length=128)


class RelationshipResponse(BaseModel):
    id: str
    data_source_id: str
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    cardinality: str
    confidence: float
    discovery_method: str
    approval_status: str
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RelationshipListResponse(BaseModel):
    items: list[RelationshipResponse]


class FreshnessResponse(BaseModel):
    data_source_id: str
    checked_at: datetime
    latest_source_timestamp: datetime | None
    stale: bool
    health_status: str
    per_table: dict[str, datetime]
