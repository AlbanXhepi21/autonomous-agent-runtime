"""Lifecycle-managed connection boundary for an external analytics database."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine


class AnalyticsDatabaseError(RuntimeError):
    """Safe domain error; callers must not expose provider exception details."""


class AnalyticsDatabase:
    """Own the analytics engine without sharing application persistence resources."""

    def __init__(self, database_url: str, *, connect_args: dict[str, Any] | None = None) -> None:
        self._database_url = database_url
        #: Passed straight to asyncpg's own connect() -- a workspace data
        #: source uses this for its SSL context (see
        #: app.datasources.security.build_ssl_context); the single process-wide
        #: ANALYTICS_DATABASE_URL leaves this unset, unchanged from before.
        self._connect_args = connect_args or {}
        self._engine: AsyncEngine | None = None

    @property
    def configured(self) -> bool:
        return bool(self._database_url)

    def _get_engine(self) -> AsyncEngine:
        if not self.configured:
            raise AnalyticsDatabaseError("Analytics database is not configured.")
        if self._engine is None:
            self._engine = create_async_engine(self._database_url, pool_pre_ping=True, connect_args=self._connect_args)
        return self._engine

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[AsyncConnection]:
        """Yield a connection without hiding errors raised by its caller.

        A try/except around ``yield`` also catches query and transaction failures,
        which used to misreport every SQL error as a database outage. Only opening
        the connection belongs to this availability boundary; query execution is
        classified by the SQL executor.
        """
        try:
            connection = await self._get_engine().connect()
        except AnalyticsDatabaseError:
            raise
        except Exception as error:
            message = str(error).lower()
            safe_message = "Analytics database permission was denied." if "permission denied" in message else "Analytics database is unavailable."
            raise AnalyticsDatabaseError(safe_message) from error
        try:
            yield connection
        finally:
            await connection.close()

    async def health_check(self) -> bool:
        try:
            async with self.connection() as connection:
                await connection.execute(text("SELECT 1"))
            return True
        except AnalyticsDatabaseError:
            return False

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
