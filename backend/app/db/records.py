"""SQLAlchemy persistence models for the database layer."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class used by Alembic metadata and SQLAlchemy mappings."""


class MemoryRecord(Base):
    """Persistent representation of a domain memory.

    ``workspace_id`` has no reliable foreign-key parent to inherit scoping
    from -- ``run_id``/``session_id`` are loose correlation strings, not
    foreign keys -- so it is a direct column here, checked on every read and
    write rather than joined.
    """

    __tablename__ = "memories"
    __table_args__ = (
        Index("ix_memories_memory_type", "memory_type"),
        Index("ix_memories_run_id", "run_id"),
        Index("ix_memories_session_id", "session_id"),
        Index("ix_memories_created_at", "created_at"),
        Index("ix_memories_workspace_type", "workspace_id", "memory_type"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConversationRecord(Base):
    """A user-visible chat context. This is intentionally separate from memories.

    ``workspace_id`` is the root of the conversation/message/run ownership
    tree -- ``messages`` and ``agent_runs`` verify tenant ownership by
    joining to this column rather than carrying their own copy of it.
    """

    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_updated_at", "updated_at"),
        Index("ix_conversations_workspace_updated_at", "workspace_id", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentRunRecord(Base):
    """Durable public summary of one runtime execution, keyed by runtime run ID."""

    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("ix_agent_runs_conversation_created_at", "conversation_id", "created_at"),
        Index("ix_agent_runs_user_message_id", "user_message_id"),
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    conversation_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False)
    user_message_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("messages.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    chart_specs: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    # The evidence an answer cited, denormalised: query identifiers are minted
    # against a process-local trace that does not survive a restart.
    answer_sources: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    # The limitations the model stated when it finished. Null on runs that
    # predate the column, which reads the same as having stated none.
    answer_caveats: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class MessageRecord(Base):
    """One visible message; `run_id` traces agent output back to its execution."""

    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_created_at", "conversation_id", "created_at"),
        Index("ix_messages_run_id", "run_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    conversation_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ArtifactRecord(Base):
    """Durable record of one downloadable output, keyed by its issued UUID.

    There is deliberately no foreign key to ``agent_runs``: artifacts are
    registered against the runtime run ID, which also covers direct agent API
    runs and sub-agent runs that never appear in conversation history.
    """

    __tablename__ = "artifacts"
    __table_args__ = (
        Index("ix_artifacts_run_id_created_at", "run_id", "created_at"),
        Index("ix_artifacts_status", "status"),
        Index("ix_artifacts_workspace_created_at", "workspace_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Provider-independent location within the artifact area, never a machine path.
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    output_format: Mapped[str | None] = mapped_column(String(16), nullable=True)
    template_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    template_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # "standard" is the only policy the retention worker ever claims; a legal
    # hold or a permanent artifact is skipped regardless of expires_at.
    retention_policy: Mapped[str] = mapped_column(String(16), nullable=False, default="standard")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Set while a retention worker owns this row; cleared on success or
    # failure. A stale claim is reclaimable, the same pattern scheduled_reports
    # uses for its own worker claim.
    deletion_claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deletion_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deletion_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class SavedReportRecord(Base):
    """A durable, reusable report recipe: what to execute again, not an output.

    ``workspace_id`` is a real foreign key -- it started as a plain scoping
    string before ``workspaces`` existed as a table; see
    ``migrations/versions/20260903_0020_finalize_workspace_columns.py`` for
    the conversion. ``seed_narrative`` is denormalised the same way
    ``answer_sources`` is on ``AgentRunRecord``: the run it was captured from
    can be deleted without silently breaking a definition that pins its
    narrative to that text.
    """

    __tablename__ = "saved_reports"
    __table_args__ = (
        Index("ix_saved_reports_workspace_status", "workspace_id", "status", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False)
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_id: Mapped[str] = mapped_column(String(64), nullable=False)
    template_version: Mapped[str] = mapped_column(String(32), nullable=False)
    metric_requests: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    default_period: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    narrative_policy: Mapped[str] = mapped_column(String(32), nullable=False)
    seed_run_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seed_narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    seed_narrative_period: Mapped[str | None] = mapped_column(String(160), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SavedReportExecutionRecord(Base):
    """One attempt to run a saved report definition, and what it produced.

    Artifacts are correlated by ``run_id`` rather than a new column on
    ``artifacts``: each execution mints its own fresh run ID, and
    ``ArtifactStore.list(run_id=...)`` already answers "what did this
    execution produce" without widening the artifact schema.
    """

    __tablename__ = "saved_report_executions"
    __table_args__ = (
        Index("ix_saved_report_executions_report_created_at", "saved_report_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    saved_report_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("saved_reports.id", ondelete="RESTRICT"), nullable=False,
    )
    # Null for an execution triggered manually (through the API); set when a
    # SchedulerWorker minted this run on the saved report's own schedule.
    scheduled_report_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("scheduled_reports.id", ondelete="SET NULL"), nullable=True,
    )
    run_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    resolved_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    resolved_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    formats: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # A closed vocabulary matching app.reliability.contracts.FailureCategory,
    # so a scheduled failure is groupable the same way a runtime one is.
    error_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    usage_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Denormalised alongside run_id -- ArtifactStore.list(run_id=...) already
    # answers this, but persisting it here keeps an execution's own record
    # self-describing even if artifact rows are later pruned.
    artifact_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScheduledReportRecord(Base):
    """A recurring instruction to run a saved report on a deterministic clock.

    Scheduled execution reuses the same deterministic semantic-metric pipeline
    a manual run does -- nothing here ever reaches the LLM. ``claimed_at``
    is this table's concurrency-safety mechanism: a worker claims a due row
    with an atomic ``UPDATE ... RETURNING`` before running it, so two workers
    polling the same table cannot both execute the same schedule.
    """

    __tablename__ = "scheduled_reports"
    __table_args__ = (
        Index("ix_scheduled_reports_due", "enabled", "next_run_at"),
        Index("ix_scheduled_reports_workspace", "workspace_id"),
        Index("ix_scheduled_reports_saved_report", "saved_report_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    saved_report_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("saved_reports.id", ondelete="RESTRICT"), nullable=False,
    )
    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False)
    schedule_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    schedule_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    formats: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    delivery_channel: Mapped[str | None] = mapped_column(String(16), nullable=True)
    delivery_destination: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_result: Mapped[str | None] = mapped_column(String(16), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DeliveryRecord(Base):
    """One attempt to hand a ready artifact to its destination.

    Never created for an artifact that is not already ``READY`` --
    ``ArtifactStore.get`` itself refuses to return a pending, failed or
    deleted artifact, so that guarantee is structural rather than a check
    this table has to repeat. ``artifact_id`` deliberately carries no foreign
    key: the artifact backend is switchable (``Settings.artifact_backend``),
    so the row it names may live in-process rather than in this database at
    all, the same reasoning ``saved_report_executions`` already applies by
    correlating to artifacts through ``run_id`` instead of a foreign key.
    """

    __tablename__ = "deliveries"
    __table_args__ = (
        Index("ix_deliveries_artifact_created_at", "artifact_id", "created_at"),
        Index("ix_deliveries_status", "status"),
        Index("ix_deliveries_workspace_status", "workspace_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    # No foreign-key parent to inherit from -- artifact_id has none either
    # (the artifact backend is switchable), so this is a direct column,
    # populated from the artifact's own workspace at delivery-creation time.
    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False)
    artifact_id: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    destination: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Sanitized before it ever reaches this column -- see app.delivery.providers.
    provider_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DataSourceRecord(Base):
    """A workspace's own read-only PostgreSQL connection.

    ``encrypted_password`` is ciphertext produced by
    ``app.datasources.encryption.SecretCipher`` -- this row never stores or
    returns a plaintext password, and no store method built on this record
    reads that column back into an API response. ``workspace_id`` is a real
    foreign key, converted from a plain scoping string once ``workspaces``
    existed as a table.
    """

    __tablename__ = "data_sources"
    __table_args__ = (
        Index("ix_data_sources_workspace", "workspace_id"),
        Index("ix_data_sources_workspace_status", "workspace_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    engine: Mapped[str] = mapped_column(String(32), nullable=False, server_default="postgresql")
    environment: Mapped[str] = mapped_column(String(16), nullable=False, server_default="development")
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=5432)
    database_name: Mapped[str] = mapped_column(String(128), nullable=False)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    ssl_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="require")
    allowed_schemas: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    statement_timeout_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=15)
    connection_timeout_seconds: Mapped[float] = mapped_column(Float, nullable=False, server_default="10")
    source_timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_result_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=5_000)
    max_result_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=1_000_000)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    health_status: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    last_connection_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_connection_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_successful_connection_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_profiled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: The user id (as text) who created this connection -- ``NULL`` for rows
    #: created before this column existed, never backfilled with a guess.
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    #: Optimistic-lock counter, bumped on every configuration or credential
    #: change -- also feeds the runtime connection pool's cache key (see
    #: ``app.datasources.pool``).
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DataSourceTableRecord(Base):
    """A selected table's governed metadata -- what an agent may be told about it.

    Never created outright "trusted": ``approved_by``/``approved_at`` record
    whether a human has actually reviewed this metadata, and ``active``
    is the on/off switch a table (or a whole later decision to exclude it)
    is read through by every tool, not just the catalog API.
    """

    __tablename__ = "data_source_tables"
    __table_args__ = (
        UniqueConstraint("data_source_id", "schema_name", "technical_name", name="uq_data_source_table"),
        Index("ix_data_source_tables_source_active", "data_source_id", "active"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    data_source_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False,
    )
    schema_name: Mapped[str] = mapped_column(String(128), nullable=False)
    technical_name: Mapped[str] = mapped_column(String(128), nullable=False)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    grain: Mapped[str | None] = mapped_column(String(500), nullable=True)
    freshness_column: Mapped[str | None] = mapped_column(String(128), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DataSourceColumnRecord(Base):
    """One column's governed role, sensitivity classification, and access.

    ``example_values`` is only ever populated when ``sensitivity`` permits it
    -- enforced by ``DataSourceColumnCatalogEntry`` before a row like this is
    ever written, not re-checked here.
    """

    __tablename__ = "data_source_columns"
    __table_args__ = (
        UniqueConstraint("data_source_table_id", "technical_name", name="uq_data_source_column"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    data_source_table_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("data_source_tables.id", ondelete="RESTRICT"), nullable=False,
    )
    technical_name: Mapped[str] = mapped_column(String(128), nullable=False)
    data_type: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="other")
    sensitivity: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    excluded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    example_values: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserRecord(Base):
    """A registered account. ``email`` is stored already normalized (trimmed, lowercased)
    -- the uniqueness index is only correct because callers never write anything else here.
    """

    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email", "email", unique=True),)

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    #: Set while an email change is awaiting confirmation at the new address.
    pending_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    preferred_timezone: Mapped[str] = mapped_column(String(64), nullable=False, server_default="UTC")
    preferred_locale: Mapped[str] = mapped_column(String(16), nullable=False, server_default="en-US")
    #: No foreign key to ``artifacts`` -- the artifact backend is switchable
    #: (in-memory or PostgreSQL) and may not share this database at all, the
    #: same reasoning ``DeliveryRecord.artifact_id`` already documents.
    profile_image_artifact_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    profile_image_workspace_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SessionRecord(Base):
    """A server-side session behind an HTTP-only cookie -- never a JWT.

    ``token_hash``/``csrf_token_hash`` are SHA-256 digests; the raw values exist
    only in the cookies issued to the browser and are never written here, the
    same discipline ``identity_tokens`` and ``data_sources.encrypted_password``
    already apply to secret material. ``user_agent``/``ip_address`` are best-effort
    device metadata for a user's own "manage sessions" view, not a security boundary.
    """

    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_token_hash", "token_hash", unique=True),
        Index("ix_sessions_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)


class IdentityTokenRecord(Base):
    """A single-use, purpose-bound recovery/verification token.

    Only ``token_hash`` is stored, matching ``sessions``. ``purpose`` keeps a
    password-reset token from being redeemable at the email-verification
    endpoint (or vice versa) even if an attacker recovered a raw value.
    """

    __tablename__ = "identity_tokens"
    __table_args__ = (
        Index("ix_identity_tokens_token_hash", "token_hash", unique=True),
        Index("ix_identity_tokens_user_purpose", "user_id", "purpose"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkspaceRecord(Base):
    """A tenant organization -- the isolation boundary every tenant-owned
    resource's ``workspace_id`` foreign key ultimately points to.
    """

    __tablename__ = "workspaces"
    __table_args__ = (Index("ix_workspaces_slug", "slug", unique=True),)

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    logo_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    default_locale: Mapped[str] = mapped_column(String(16), nullable=False, default="en-US")
    default_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    fiscal_year_start_month: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    number_format: Mapped[str] = mapped_column(String(32), nullable=False, server_default="1,234.56")
    date_format: Mapped[str] = mapped_column(String(32), nullable=False, server_default="YYYY-MM-DD")
    #: Optimistic-concurrency counter -- see ``app.tenancy.store.WorkspaceStore.update``.
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReportPreferencesRecord(Base):
    """A workspace's defaults for producing a report -- presentation choices
    only, never a fact about the data (see ``app.tenancy.contracts.ReportPreferences``).
    """

    __tablename__ = "report_preferences"

    workspace_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True,
    )
    default_template: Mapped[str | None] = mapped_column(String(128), nullable=True)
    default_output_format: Mapped[str | None] = mapped_column(String(8), nullable=True)
    default_theme: Mapped[str | None] = mapped_column(String(128), nullable=True)
    default_narrative_policy: Mapped[str | None] = mapped_column(String(32), nullable=True)
    evidence_appendix_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    technical_sql_appendix_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditLogEntryRecord(Base):
    """An append-only record of a security-relevant change. Never updated or
    deleted by application code once written (see ``app.audit.store``).
    """

    __tablename__ = "audit_log_entries"
    __table_args__ = (
        Index("ix_audit_log_entries_workspace", "workspace_id", "created_at"),
        Index("ix_audit_log_entries_actor", "actor_user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    workspace_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    event_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkspaceMembershipRecord(Base):
    """One user's standing in one workspace.

    ``uq_workspace_membership_user_workspace`` is what "prevent duplicate
    user/tenant memberships" actually rests on -- a user has at most one
    membership row per workspace, active or disabled, ever. There is no
    reactivation path in this phase: once removed, rejoining is out of
    scope (see app.tenancy.service module docstring).
    """

    __tablename__ = "workspace_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "workspace_id", name="uq_workspace_membership_user_workspace"),
        Index("ix_workspace_memberships_workspace", "workspace_id"),
        Index("ix_workspace_memberships_user", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    invited_by: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkspaceInvitationRecord(Base):
    """A pending offer to join a workspace at a given role.

    Bound to a normalized email, not a user id -- the invitee may not have
    an account yet; acceptance re-checks that the accepting user's own
    email matches. The partial unique index enforces "no duplicate pending
    invitation for the same (workspace, email)" at the database level, not
    just in the service -- a row that has already been accepted or revoked
    does not block a fresh invitation from being sent again.
    """

    __tablename__ = "workspace_invitations"
    __table_args__ = (
        Index("ix_workspace_invitations_token_hash", "token_hash", unique=True),
        Index(
            "ix_workspace_invitations_pending_unique", "workspace_id", "email",
            unique=True, postgresql_where=text("accepted_at IS NULL AND revoked_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    invited_by: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DataSourceRelationshipRecord(Base):
    """One join between two tables of the same connection, discovered or declared.

    A discovered relationship never becomes a trusted, agent-visible join by
    itself: ``get_table_relationships`` only ever returns rows with
    ``approval_status == "approved"``, regardless of ``confidence``.
    """

    __tablename__ = "data_source_relationships"
    __table_args__ = (
        Index("ix_data_source_relationships_source_status", "data_source_id", "approval_status"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    data_source_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False,
    )
    source_table: Mapped[str] = mapped_column(String(128), nullable=False)
    source_column: Mapped[str] = mapped_column(String(128), nullable=False)
    target_table: Mapped[str] = mapped_column(String(128), nullable=False)
    target_column: Mapped[str] = mapped_column(String(128), nullable=False)
    cardinality: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    discovery_method: Mapped[str] = mapped_column(String(16), nullable=False)
    approval_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
