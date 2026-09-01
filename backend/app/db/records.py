"""SQLAlchemy persistence models for the database layer."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class used by Alembic metadata and SQLAlchemy mappings."""


class MemoryRecord(Base):
    """Persistent representation of a domain memory."""

    __tablename__ = "memories"
    __table_args__ = (
        Index("ix_memories_memory_type", "memory_type"),
        Index("ix_memories_run_id", "run_id"),
        Index("ix_memories_session_id", "session_id"),
        Index("ix_memories_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConversationRecord(Base):
    """A user-visible chat context. This is intentionally separate from memories."""

    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_updated_at", "updated_at"),)

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
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
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
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
