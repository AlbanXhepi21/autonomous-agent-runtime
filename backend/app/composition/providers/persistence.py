"""Durable stores backed by the runtime database."""

from app.composition.lifecycle import provider
from app.composition.providers.settings import get_settings
from app.conversations.store import ConversationStore, PostgresConversationStore
from app.memory.in_memory import InMemoryMemoryStore
from app.memory.manager import MemoryManager
from app.memory.retrieval import MemoryRetriever
from app.memory.store import MemoryStore
from app.memory.writing import MemoryWritingPipeline


@provider
def get_conversation_store() -> ConversationStore:
    """Use the existing runtime PostgreSQL database for durable UI history."""

    from app.db.session import Database

    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required for persistent conversation history")
    return PostgresConversationStore(Database(settings.database_url))


@provider
def get_memory_store() -> MemoryStore:
    """Build the configured storage implementation without involving the runtime."""

    settings = get_settings()
    if settings.memory_backend == "in_memory":
        return InMemoryMemoryStore()
    from app.db.session import Database
    from app.memory.postgres import PostgresMemoryStore

    return PostgresMemoryStore(Database(settings.database_url))


@provider
def get_memory_manager() -> MemoryManager:
    """Return the application-scoped memory manager and its selected store."""

    return MemoryManager(get_memory_store())


@provider
def get_memory_retriever() -> MemoryRetriever:
    """Return the shared selector over the configured persistent memory store."""

    return MemoryRetriever(get_memory_store())


@provider
def get_memory_writer() -> MemoryWritingPipeline:
    """Return the policy-gated writer for completed-run memory candidates."""

    return MemoryWritingPipeline(get_memory_manager())
