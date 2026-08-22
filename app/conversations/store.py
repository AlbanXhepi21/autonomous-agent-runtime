"""PostgreSQL repository for visible conversation and run history."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import AgentRunRecord, ConversationRecord, MessageRecord
from app.db.session import Database

DEFAULT_CONVERSATION_TITLE = "New conversation"


def now() -> datetime:
    return datetime.now(timezone.utc)


def generate_title(message: str) -> str:
    """Create a stable, local title without spending an LLM call."""

    cleaned = re.sub(r"\s+", " ", message).strip().rstrip("?!.")
    lowered = cleaned.lower()
    month = next((item for item in ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December") if item.lower() in lowered), None)
    if "revenue" in lowered and any(word in lowered for word in ("fall", "fell", "decline", "drop", "decrease")):
        return f"{month + ' ' if month else ''}revenue decline"
    words = re.sub(r"^(why|what|how|can you|please|analyze|analyse|show me)\s+", "", cleaned, flags=re.I).split()
    title = " ".join(words[:5]).strip()
    return (title[:1].upper() + title[1:])[:255] if title else DEFAULT_CONVERSATION_TITLE


def should_generate_title(title: str, has_messages: bool) -> bool:
    """Only replace the placeholder title of a conversation's first message."""

    return title == DEFAULT_CONVERSATION_TITLE and not has_messages


class ConversationStore:
    """Persistence contract for conversation history; never reads or writes memory."""

    async def create_conversation(self, title: str = DEFAULT_CONVERSATION_TITLE) -> ConversationRecord: raise NotImplementedError
    async def list_conversations(self, *, limit: int, offset: int) -> tuple[list[ConversationRecord], int]: raise NotImplementedError
    async def get_conversation(self, conversation_id: UUID) -> ConversationRecord | None: raise NotImplementedError
    async def update_title(self, conversation_id: UUID, title: str) -> ConversationRecord | None: raise NotImplementedError
    async def delete_conversation(self, conversation_id: UUID) -> bool: raise NotImplementedError
    async def list_messages(self, conversation_id: UUID, *, limit: int, offset: int) -> tuple[list[MessageRecord], int]: raise NotImplementedError
    async def list_runs(self, conversation_id: UUID) -> list[AgentRunRecord]: raise NotImplementedError
    async def get_run(self, run_id: str) -> AgentRunRecord | None: raise NotImplementedError
    async def get_assistant_message_for_run(self, run_id: str) -> MessageRecord | None: raise NotImplementedError
    async def create_run(self, *, conversation_id: UUID | None, message: str, run_id: str) -> tuple[ConversationRecord, MessageRecord, AgentRunRecord]: raise NotImplementedError
    async def start_run(self, run_id: str, started_at: datetime) -> None: raise NotImplementedError
    async def finish_run(self, *, run_id: str, status: str, completed_at: datetime, metrics: dict[str, object] | None, chart_specs: list[dict[str, object]] | None, error: str | None, assistant_content: str | None) -> None: raise NotImplementedError


class PostgresConversationStore(ConversationStore):
    def __init__(self, database: Database) -> None: self._database = database

    async def close(self) -> None:
        """Release the connection pool this store owns, at application shutdown."""

        await self._database.dispose()

    async def create_conversation(self, title: str = DEFAULT_CONVERSATION_TITLE) -> ConversationRecord:
        record = ConversationRecord(id=uuid4(), title=title, created_at=now(), updated_at=now())
        await self._commit(lambda session: session.add(record))
        return record

    async def list_conversations(self, *, limit: int, offset: int) -> tuple[list[ConversationRecord], int]:
        from sqlalchemy import func
        async with self._database.session() as session:
            total = await session.scalar(select(func.count()).select_from(ConversationRecord)) or 0
            records = (await session.scalars(select(ConversationRecord).order_by(ConversationRecord.updated_at.desc(), ConversationRecord.id.desc()).limit(limit).offset(offset))).all()
        return records, total

    async def get_conversation(self, conversation_id: UUID) -> ConversationRecord | None:
        async with self._database.session() as session: return await session.get(ConversationRecord, conversation_id)

    async def update_title(self, conversation_id: UUID, title: str) -> ConversationRecord | None:
        async with self._database.session() as session:
            async with session.begin():
                record = await session.get(ConversationRecord, conversation_id)
                if record is None: return None
                record.title, record.updated_at = title, now()
                return record

    async def delete_conversation(self, conversation_id: UUID) -> bool:
        # Runs and messages are history scoped to the conversation; runtime artifacts are not touched.
        async with self._database.session() as session:
            async with session.begin():
                record = await session.get(ConversationRecord, conversation_id)
                if record is None: return False
                await session.execute(delete(AgentRunRecord).where(AgentRunRecord.conversation_id == conversation_id))
                await session.execute(delete(MessageRecord).where(MessageRecord.conversation_id == conversation_id))
                await session.delete(record)
        return True

    async def list_messages(self, conversation_id: UUID, *, limit: int, offset: int) -> tuple[list[MessageRecord], int]:
        from sqlalchemy import func
        async with self._database.session() as session:
            total = await session.scalar(select(func.count()).select_from(MessageRecord).where(MessageRecord.conversation_id == conversation_id)) or 0
            records = (await session.scalars(select(MessageRecord).where(MessageRecord.conversation_id == conversation_id).order_by(MessageRecord.created_at, MessageRecord.id).limit(limit).offset(offset))).all()
        return records, total

    async def list_runs(self, conversation_id: UUID) -> list[AgentRunRecord]:
        async with self._database.session() as session:
            return (await session.scalars(select(AgentRunRecord).where(AgentRunRecord.conversation_id == conversation_id).order_by(AgentRunRecord.created_at, AgentRunRecord.id))).all()

    async def get_run(self, run_id: str) -> AgentRunRecord | None:
        async with self._database.session() as session:
            return await session.get(AgentRunRecord, run_id)

    async def get_assistant_message_for_run(self, run_id: str) -> MessageRecord | None:
        """Return the durable visible answer produced by a completed run."""

        async with self._database.session() as session:
            return await session.scalar(
                select(MessageRecord)
                .where(MessageRecord.run_id == run_id, MessageRecord.role == "assistant")
                .order_by(MessageRecord.created_at.desc(), MessageRecord.id.desc())
                .limit(1)
            )

    async def create_run(self, *, conversation_id: UUID | None, message: str, run_id: str) -> tuple[ConversationRecord, MessageRecord, AgentRunRecord]:
        async with self._database.session() as session:
            async with session.begin():
                stamp = now()
                conversation = await session.get(ConversationRecord, conversation_id) if conversation_id else None
                if conversation_id and conversation is None: raise LookupError("Conversation not found")
                if conversation is None:
                    conversation = ConversationRecord(id=uuid4(), title=generate_title(message), created_at=stamp, updated_at=stamp)
                    session.add(conversation)
                elif should_generate_title(
                    conversation.title,
                    (await session.scalar(
                        select(MessageRecord.id).where(MessageRecord.conversation_id == conversation.id).limit(1)
                    )) is not None,
                ):
                    conversation.title = generate_title(message)
                conversation.updated_at = stamp
                user_message = MessageRecord(id=uuid4(), conversation_id=conversation.id, role="user", content=message, created_at=stamp, run_id=None)
                # There are no ORM relationships between these history records.
                # Flush parents first so PostgreSQL never sees the run before its
                # conversation/message foreign-key targets.
                session.add(user_message)
                await session.flush()
                run = AgentRunRecord(id=run_id, conversation_id=conversation.id, user_message_id=user_message.id, status="running", created_at=stamp, started_at=None, completed_at=None, metrics=None, chart_specs=None, error=None)
                session.add(run)
            return conversation, user_message, run

    async def start_run(self, run_id: str, started_at: datetime) -> None:
        async with self._database.session() as session:
            async with session.begin():
                record = await session.get(AgentRunRecord, run_id)
                if record: record.started_at = started_at

    async def finish_run(self, *, run_id: str, status: str, completed_at: datetime, metrics: dict[str, object] | None, chart_specs: list[dict[str, object]] | None, error: str | None, assistant_content: str | None) -> None:
        async with self._database.session() as session:
            async with session.begin():
                run = await session.get(AgentRunRecord, run_id)
                if run is None: return
                run.status, run.completed_at, run.metrics, run.chart_specs, run.error = status, completed_at, metrics, chart_specs, error
                conversation = await session.get(ConversationRecord, run.conversation_id)
                if conversation: conversation.updated_at = completed_at
                if status == "completed" and assistant_content:
                    session.add(MessageRecord(id=uuid4(), conversation_id=run.conversation_id, role="assistant", content=assistant_content, created_at=completed_at, run_id=run_id))

    async def _commit(self, operation) -> None:
        try:
            async with self._database.session() as session:
                async with session.begin(): operation(session)
        except SQLAlchemyError as error:
            raise RuntimeError("Conversation storage operation failed") from error
