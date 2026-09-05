"""DataSourceRuntimePool: cache one live runtime per (workspace, data source, version)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.datasources import pool as pool_module
from app.datasources.contracts import DataSourceConnection, DataSourceConnectionConfig
from app.datasources.pool import DataSourceRuntimePool


class _FakeEngineDatabase:
    def __init__(self) -> None:
        self.disposed = False

    async def dispose(self) -> None:
        self.disposed = True


class _FakeRuntime:
    def __init__(self) -> None:
        self.database = _FakeEngineDatabase()


def _connection(*, workspace_id=None, data_source_id=None, version: int = 1) -> DataSourceConnection:
    now = datetime.now(UTC)
    return DataSourceConnection(
        id=data_source_id or uuid4(), workspace_id=workspace_id or uuid4(), name="Primary",
        config=DataSourceConnectionConfig(host="db.example.com", database="analytics", username="ro", allowed_schemas=["public"]),
        status="active", health_status="healthy", version=version, created_at=now, updated_at=now,
    )


@pytest.fixture(autouse=True)
def _fake_runtime_builder(monkeypatch: pytest.MonkeyPatch) -> list[_FakeRuntime]:
    """Replace the real (socket-opening) runtime builder with a counter of fakes."""

    built: list[_FakeRuntime] = []

    def _build(*_args: object, **_kwargs: object) -> _FakeRuntime:
        runtime = _FakeRuntime()
        built.append(runtime)
        return runtime

    monkeypatch.setattr(pool_module, "build_data_source_runtime", _build)
    return built


async def _password() -> str:
    return "super-secret"


@pytest.mark.asyncio
async def test_acquire_builds_once_and_reuses_the_cached_runtime(_fake_runtime_builder: list[_FakeRuntime]) -> None:
    pool = DataSourceRuntimePool()
    connection = _connection()

    first = await pool.acquire(connection, password_factory=_password)
    second = await pool.acquire(connection, password_factory=_password)

    assert first is second
    assert len(_fake_runtime_builder) == 1


@pytest.mark.asyncio
async def test_acquire_only_calls_the_password_factory_on_a_cache_miss(_fake_runtime_builder: list[_FakeRuntime]) -> None:
    pool = DataSourceRuntimePool()
    connection = _connection()
    calls = 0

    async def _counting_password() -> str:
        nonlocal calls
        calls += 1
        return "super-secret"

    await pool.acquire(connection, password_factory=_counting_password)
    await pool.acquire(connection, password_factory=_counting_password)

    assert calls == 1


@pytest.mark.asyncio
async def test_a_new_version_builds_a_separate_runtime(_fake_runtime_builder: list[_FakeRuntime]) -> None:
    pool = DataSourceRuntimePool()
    data_source_id, workspace_id = uuid4(), uuid4()
    v1 = _connection(workspace_id=workspace_id, data_source_id=data_source_id, version=1)
    v2 = _connection(workspace_id=workspace_id, data_source_id=data_source_id, version=2)

    runtime_v1 = await pool.acquire(v1, password_factory=_password)
    runtime_v2 = await pool.acquire(v2, password_factory=_password)

    assert runtime_v1 is not runtime_v2
    assert len(_fake_runtime_builder) == 2


@pytest.mark.asyncio
async def test_invalidate_disposes_and_evicts_every_version_for_that_data_source(_fake_runtime_builder: list[_FakeRuntime]) -> None:
    pool = DataSourceRuntimePool()
    data_source_id, workspace_id = uuid4(), uuid4()
    v1 = _connection(workspace_id=workspace_id, data_source_id=data_source_id, version=1)
    v2 = _connection(workspace_id=workspace_id, data_source_id=data_source_id, version=2)
    runtime_v1 = await pool.acquire(v1, password_factory=_password)
    runtime_v2 = await pool.acquire(v2, password_factory=_password)

    await pool.invalidate(workspace_id=workspace_id, data_source_id=data_source_id)

    assert runtime_v1.database.disposed is True
    assert runtime_v2.database.disposed is True
    # A fresh acquire after invalidation must build again, not resurrect the old entry.
    rebuilt = await pool.acquire(v1, password_factory=_password)
    assert rebuilt is not runtime_v1
    assert len(_fake_runtime_builder) == 3


@pytest.mark.asyncio
async def test_invalidate_does_not_affect_another_data_sources_pooled_runtime(_fake_runtime_builder: list[_FakeRuntime]) -> None:
    pool = DataSourceRuntimePool()
    workspace_id = uuid4()
    connection_a = _connection(workspace_id=workspace_id, data_source_id=uuid4())
    connection_b = _connection(workspace_id=workspace_id, data_source_id=uuid4())
    runtime_a = await pool.acquire(connection_a, password_factory=_password)
    runtime_b = await pool.acquire(connection_b, password_factory=_password)

    await pool.invalidate(workspace_id=workspace_id, data_source_id=connection_a.id)

    assert runtime_a.database.disposed is True
    assert runtime_b.database.disposed is False


@pytest.mark.asyncio
async def test_dispose_tears_down_every_cached_runtime(_fake_runtime_builder: list[_FakeRuntime]) -> None:
    pool = DataSourceRuntimePool()
    runtime_a = await pool.acquire(_connection(), password_factory=_password)
    runtime_b = await pool.acquire(_connection(), password_factory=_password)

    await pool.dispose()

    assert runtime_a.database.disposed is True
    assert runtime_b.database.disposed is True
