"""A process-scoped cache of live runtimes, one per active connection.

``build_data_source_runtime`` is cheap to *call*, but the ``AnalyticsDatabase``
it returns owns a real SQLAlchemy async engine -- itself a connection pool.
Building a fresh one for every agent run (as the caller used to do, disposing
it again once the run finished) meant a brand new TCP/TLS handshake and
connection pool per run against the same workspace connection, even for two
runs seconds apart. This module keeps one runtime alive per
``(workspace_id, data_source_id, version)`` instead, so repeated runs against
the same, unchanged connection reuse the same pool.

``version`` is part of the key rather than something this module updates in
place: a config or credential change produces a new ``DataSourceConnection``
with a bumped version, which naturally misses the old cache entry and builds
a fresh runtime under the new key. The *old* entry is not simply abandoned,
though -- it would otherwise leak its engine forever, holding open sockets to
a connection's now-stale (or, for a credential rotation, no-longer-valid)
role. ``invalidate`` is how a caller (``DataSourceOnboardingService``, on any
configuration change, credential replacement, disable, or delete) disposes
every cached entry for a data source regardless of which version they were
built under.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

from app.core.logging import log_event, safe_error_message
from app.datasources.contracts import DataSourceConnection
from app.datasources.runtime import DataSourceRuntime, build_data_source_runtime

_logger = logging.getLogger(__name__)

_PoolKey = tuple[UUID, UUID, int]


class DataSourceRuntimePool:
    """Cache one live ``DataSourceRuntime`` per (workspace, data source, version)."""

    def __init__(self, *, allow_local_hosts: bool = False, schema_cache_ttl_seconds: float = 300) -> None:
        self._allow_local_hosts = allow_local_hosts
        self._schema_cache_ttl_seconds = schema_cache_ttl_seconds
        self._entries: dict[_PoolKey, DataSourceRuntime] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _key(connection: DataSourceConnection) -> _PoolKey:
        return (connection.workspace_id, connection.id, connection.version)

    async def acquire(
        self, connection: DataSourceConnection, *, password_factory: Callable[[], Awaitable[str]],
    ) -> DataSourceRuntime:
        """Return the cached runtime for this exact connection version, building one if needed.

        ``password_factory`` is only called -- and the password only ever
        decrypted -- on a cache miss, so a hot connection never re-touches
        its ciphertext just to serve another run.
        """

        key = self._key(connection)
        async with self._lock:
            cached = self._entries.get(key)
            if cached is not None:
                return cached

        password = await password_factory()
        runtime = build_data_source_runtime(
            connection, password=password, allow_local_hosts=self._allow_local_hosts,
            schema_cache_ttl_seconds=self._schema_cache_ttl_seconds,
        )
        async with self._lock:
            # Another caller may have raced this one to a cold key.
            existing = self._entries.get(key)
            if existing is not None:
                await runtime.database.dispose()
                return existing
            self._entries[key] = runtime
            return runtime

    async def invalidate(self, *, workspace_id: UUID, data_source_id: UUID) -> None:
        """Dispose and evict every cached runtime for this data source, any version."""

        async with self._lock:
            stale_keys = [
                key for key in self._entries
                if key[0] == workspace_id and key[1] == data_source_id
            ]
            stale = [self._entries.pop(key) for key in stale_keys]
        for runtime in stale:
            try:
                await runtime.database.dispose()
            except Exception as error:  # noqa: BLE001 - best-effort disposal, must not block invalidation
                log_event(
                    _logger, logging.WARNING, "datasource_pool_dispose_failed",
                    workspace_id=str(workspace_id), data_source_id=str(data_source_id),
                    error=safe_error_message(error),
                )

    async def dispose(self) -> None:
        """Dispose every cached runtime -- called once, at process shutdown."""

        async with self._lock:
            stale = list(self._entries.values())
            self._entries.clear()
        for runtime in stale:
            try:
                await runtime.database.dispose()
            except Exception as error:  # noqa: BLE001 - best-effort disposal, must not block shutdown
                log_event(_logger, logging.WARNING, "datasource_pool_dispose_failed", error=safe_error_message(error))
