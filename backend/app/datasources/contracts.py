"""A workspace's own PostgreSQL data source, and the governed catalog on it.

A connection describes *how to reach* a workspace's database; a catalog entry
describes *what an agent may be told* about one table in it, approved by a
human. The two are deliberately separate models: onboarding can discover a
table long before anyone has approved what it means, and a discovered
relationship is never presented to the agent as trustworthy until a human
marks it approved -- see ``approval_status`` below and
``app.datasources.service`` for where that gate is enforced.

Nothing here ever carries a plaintext password. ``DataSourceConnection`` is
safe to log, return from an API, or hold in memory past the single onboarding
request that needed the decrypted secret -- see ``app.datasources.encryption``
for how the secret itself is stored.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.analytics.schema.contracts import DatabaseColumn

SSLMode = Literal["require", "verify-ca", "verify-full"]
DataSourceStatus = Literal["pending", "testing", "verified_read_only", "active", "failed", "disabled"]
HealthStatus = Literal["healthy", "degraded", "unreachable", "unknown"]

ColumnRole = Literal["primary_key", "dimension", "measure", "time", "identifier", "other"]
SensitivityClassification = Literal[
    "public", "internal", "personal_data", "financial_data", "authentication_secret", "restricted",
]
RelationshipCardinality = Literal["one_to_one", "one_to_many", "many_to_one", "many_to_many"]
RelationshipSource = Literal["foreign_key", "inferred"]
RelationshipApprovalStatus = Literal["pending", "approved", "rejected"]

#: A column classified into any of these must never carry sampled example
#: values, whatever a caller asks for -- enforced structurally below, not
#: just by convention at the call site that populates them.
SENSITIVE_CLASSIFICATIONS: frozenset[str] = frozenset({
    "personal_data", "financial_data", "authentication_secret", "restricted",
})


class DataSourceConnectionConfig(BaseModel):
    """Everything needed to reach a workspace's database, minus the secret."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=5432, ge=1, le=65_535)
    database: str = Field(min_length=1, max_length=128)
    username: str = Field(min_length=1, max_length=128)
    #: "disable" and "allow" both permit a silent plaintext fallback and are
    #: refused outright -- see app.datasources.security.
    ssl_mode: SSLMode = "require"
    allowed_schemas: list[str] = Field(min_length=1, max_length=20)
    statement_timeout_seconds: float = Field(default=15, gt=0, le=120)
    max_result_rows: int = Field(default=5_000, ge=1, le=50_000)
    max_result_bytes: int = Field(default=1_000_000, ge=1_024)

    @model_validator(mode="after")
    def _schemas_are_unique(self) -> DataSourceConnectionConfig:
        if len(set(self.allowed_schemas)) != len(self.allowed_schemas):
            raise ValueError("A schema may be listed only once.")
        return self


class DataSourceConnection(BaseModel):
    """The durable record of one workspace's connection to its own database."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    workspace_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    config: DataSourceConnectionConfig
    status: DataSourceStatus
    health_status: HealthStatus
    last_connection_at: datetime | None = None
    last_connection_error: str | None = Field(default=None, max_length=500)
    last_profiled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ConnectionTestResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    success: bool
    message: str = Field(max_length=500)
    server_version: str | None = Field(default=None, max_length=128)


class ReadOnlyVerification(BaseModel):
    """What onboarding step 3 ("verify read-only behavior") actually checked.

    Two independent checks, not one: the role's own catalog privileges
    (``role_is_superuser`` etc., true defense-in-depth against a role that
    could write even if the application forgot to scope a transaction), and
    a live probe confirming this specific server actually enforces
    ``SET TRANSACTION READ ONLY`` for this role. Both must pass.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    is_read_only: bool
    role_is_superuser: bool
    role_can_create_database: bool
    role_can_create_role: bool
    role_bypasses_row_level_security: bool
    message: str = Field(max_length=500)


class DataSourceColumnCatalogEntry(BaseModel):
    """One column's governed classification -- role, sensitivity, and access."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    table_id: UUID
    technical_name: str = Field(min_length=1, max_length=128)
    data_type: str = Field(min_length=1, max_length=64)
    role: ColumnRole = "other"
    sensitivity: SensitivityClassification = "internal"
    #: Excluded from every tool's view of this table -- describe_table,
    #: search_schema, and query_database's own allowed-column projection all
    #: honor this, not just the catalog API.
    excluded: bool = False
    example_values: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _sensitive_columns_never_carry_examples(self) -> DataSourceColumnCatalogEntry:
        if self.sensitivity in SENSITIVE_CLASSIFICATIONS and self.example_values:
            raise ValueError(f"A {self.sensitivity} column must not carry sampled example values.")
        return self


class DataSourceTableCatalogEntry(BaseModel):
    """One selected table's governed metadata -- what an agent is told about it.

    ``active`` is the table-level exclusion switch; an inactive table is
    invisible to every tool exactly as if it had never been selected.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    data_source_id: UUID
    schema_name: str = Field(min_length=1, max_length=128)
    technical_name: str = Field(min_length=1, max_length=128)
    business_name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2_000)
    grain: str | None = Field(default=None, max_length=500)
    freshness_column: str | None = Field(default=None, max_length=128)
    active: bool = True
    approved_by: str | None = Field(default=None, max_length=128)
    approved_at: datetime | None = None
    columns: list[DataSourceColumnCatalogEntry] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @property
    def primary_key(self) -> list[str]:
        return [column.technical_name for column in self.columns if column.role == "primary_key"]

    @property
    def dimensions(self) -> list[str]:
        return [column.technical_name for column in self.columns if column.role == "dimension"]

    @property
    def measures(self) -> list[str]:
        return [column.technical_name for column in self.columns if column.role == "measure"]

    @property
    def time_columns(self) -> list[str]:
        return [column.technical_name for column in self.columns if column.role == "time"]

    @property
    def sensitive_columns(self) -> list[str]:
        return [column.technical_name for column in self.columns if column.sensitivity in SENSITIVE_CLASSIFICATIONS]

    @property
    def excluded_columns(self) -> list[str]:
        return [column.technical_name for column in self.columns if column.excluded]


class DataSourceRelationship(BaseModel):
    """One approved-or-pending join between two tables in the same connection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    data_source_id: UUID
    source_table: str = Field(min_length=1, max_length=128)
    source_column: str = Field(min_length=1, max_length=128)
    target_table: str = Field(min_length=1, max_length=128)
    target_column: str = Field(min_length=1, max_length=128)
    cardinality: RelationshipCardinality
    confidence: float = Field(ge=0.0, le=1.0)
    #: "foreign_key" -- read straight from a database constraint, confidence
    #: always 1.0. "inferred" -- a naming-convention heuristic candidate,
    #: confidence < 1.0, and never trusted until approved regardless of score.
    discovery_method: RelationshipSource
    approval_status: RelationshipApprovalStatus = "pending"
    approved_by: str | None = Field(default=None, max_length=128)
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RelationshipCandidate(BaseModel):
    """One discovery result, before it becomes a persisted, reviewable row."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_table: str = Field(min_length=1, max_length=128)
    source_column: str = Field(min_length=1, max_length=128)
    target_table: str = Field(min_length=1, max_length=128)
    target_column: str = Field(min_length=1, max_length=128)
    cardinality: RelationshipCardinality
    confidence: float = Field(ge=0.0, le=1.0)
    discovery_method: RelationshipSource


class TableProfile(BaseModel):
    """What onboarding step 6 ("profile selected tables") produced."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_name: str = Field(min_length=1, max_length=128)
    technical_name: str = Field(min_length=1, max_length=128)
    row_count_estimate: int | None = Field(default=None, ge=0)
    columns: list[DatabaseColumn]
    profiled_at: datetime


class FreshnessSnapshot(BaseModel):
    """What's known about how current a connection's active data is."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    data_source_id: UUID
    checked_at: datetime
    latest_source_timestamp: datetime | None = None
    stale: bool
    health_status: HealthStatus
    #: One entry per active table that named a freshness_column; a table
    #: without one simply has no key here, not a null placeholder.
    per_table: dict[str, datetime] = Field(default_factory=dict)
