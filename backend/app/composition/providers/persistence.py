"""Durable stores backed by the runtime database."""

from typing import TYPE_CHECKING

from app.composition.lifecycle import provider
from app.composition.providers.settings import get_settings
from app.conversations.store import ConversationStore, PostgresConversationStore
from app.memory.in_memory import InMemoryMemoryStore
from app.memory.manager import MemoryManager
from app.memory.retrieval import MemoryRetriever
from app.memory.store import MemoryStore
from app.memory.writing import MemoryWritingPipeline
from app.reports.store import PostgresSavedReportStore, SavedReportStore

if TYPE_CHECKING:
    from app.db.session import Database


@provider
def get_runtime_database() -> "Database":
    """Own the one runtime connection pool every durable store shares.

    Each store previously built its own ``Database``, which meant a second pool
    per store and a teardown order nobody had reasoned about. Building it here
    means the pool is constructed once, registered for disposal once, and closed
    after the stores that borrow it.
    """

    from app.db.session import Database

    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required for durable runtime storage")
    return Database(settings.database_url)


@provider
def get_conversation_store() -> ConversationStore:
    """Use the existing runtime PostgreSQL database for durable UI history."""

    return PostgresConversationStore(get_runtime_database())


@provider
def get_memory_store() -> MemoryStore:
    """Build the configured storage implementation without involving the runtime."""

    settings = get_settings()
    if settings.memory_backend == "in_memory":
        return InMemoryMemoryStore()
    from app.memory.postgres import PostgresMemoryStore

    return PostgresMemoryStore(get_runtime_database())


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


@provider
def get_saved_report_store() -> SavedReportStore:
    """Use the existing runtime PostgreSQL database for saved report definitions."""

    return PostgresSavedReportStore(get_runtime_database())
