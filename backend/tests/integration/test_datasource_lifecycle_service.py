"""Administrative connection lifecycle -- edit, replace credentials, disable/enable,
soft-delete, connection pooling, and audit logging -- against real PostgreSQL.

Builds on the same fixtures as ``test_datasource_onboarding_service.py``
(a throwaway, genuinely read-only role connecting back to this suite's own
database) rather than re-deriving them, per this repository's convention of
one canonical live-connection fixture set for data source tests.
"""

from __future__ import annotations

import uuid

import pytest
from cryptography.fernet import Fernet
from pytest_asyncio import fixture

pytest.importorskip("sqlalchemy")

from app.audit.store import InMemoryAuditLogStore
from app.datasources.encryption import FernetSecretCipher
from app.datasources.pool import DataSourceRuntimePool
from app.datasources.service import DataSourceOnboardingError, DataSourceOnboardingService, DataSourceStateError
from app.datasources.store import PostgresDataSourceStore
from app.db.session import Database
from tests.integration.test_datasource_onboarding_service import (
    TEST_DATABASE_URL,
    WORKSPACE,
    _config,
    _FixedCredentialProvider,
    _purge,
    admin_dsn,  # noqa: F401 - reused as a pytest fixture, referenced by parameter name below
    restricted_role,  # noqa: F401 - reused as a pytest fixture, referenced by parameter name below
)

pytestmark = pytest.mark.postgres


@fixture
async def audited_service(admin_dsn):  # noqa: F811 - pytest fixture injection, not a redefinition
    await _purge()
    database = Database(TEST_DATABASE_URL)
    cipher = FernetSecretCipher(_FixedCredentialProvider(Fernet.generate_key().decode()))
    audit = InMemoryAuditLogStore()
    pool = DataSourceRuntimePool(allow_local_hosts=True)
    store = PostgresDataSourceStore(database)
    try:
        yield DataSourceOnboardingService(
            store=store, cipher=cipher, audit=audit, runtime_pool=pool, allow_local_hosts=True,
        ), audit, pool
    finally:
        await pool.dispose()
        await database.dispose()
        await _purge()


@fixture
async def onboarded(audited_service, restricted_role):  # noqa: F811 - pytest fixture injection, not a redefinition
    """An activated connection, plus the same service/audit/pool and credentials, ready for a lifecycle action."""

    service, audit, pool = audited_service
    url, role_name, password = restricted_role
    connection = await service.create_connection(
        workspace_id=WORKSPACE, name="Primary Analytics",
        config=_config(url).model_copy(update={"username": role_name}), password=password,
        description="A throwaway read-only role", environment="staging", actor_user_id=uuid.uuid4(),
    )
    await service.test_connectivity(workspace_id=WORKSPACE, data_source_id=connection.id)
    await service.verify_read_only_behavior(workspace_id=WORKSPACE, data_source_id=connection.id)
    table = await service.select_and_profile_table(
        workspace_id=WORKSPACE, data_source_id=connection.id, schema_name="public",
        technical_name="conversations", business_name="Conversations",
    )
    await service._store.approve_table(workspace_id=WORKSPACE, data_source_id=connection.id, table_id=table.id, approved_by="alice")
    activated = await service.activate(workspace_id=WORKSPACE, data_source_id=connection.id)
    return service, audit, pool, activated, password


@pytest.mark.asyncio
async def test_create_connection_records_environment_engine_and_creator(audited_service, restricted_role) -> None:  # noqa: F811
    service, audit, _pool = audited_service
    url, role_name, password = restricted_role
    actor = uuid.uuid4()

    connection = await service.create_connection(
        workspace_id=WORKSPACE, name="Primary Analytics",
        config=_config(url).model_copy(update={"username": role_name}), password=password,
        description="Read replica", engine="postgresql", environment="production", actor_user_id=actor,
    )

    assert connection.environment == "production"
    assert connection.engine == "postgresql"
    assert connection.description == "Read replica"
    assert connection.created_by == str(actor)
    assert connection.version == 1

    entries = await audit.list_for_workspace(workspace_id=WORKSPACE)
    assert any(entry.event_type == "datasource_created" for entry in entries)


@pytest.mark.asyncio
async def test_active_connection_runtime_reuses_the_same_pooled_runtime(onboarded) -> None:
    service, _audit, _pool, _activated, _password = onboarded

    _connection_1, runtime_1 = await service.active_connection_runtime(workspace_id=WORKSPACE)
    _connection_2, runtime_2 = await service.active_connection_runtime(workspace_id=WORKSPACE)

    assert runtime_1 is runtime_2


@pytest.mark.asyncio
async def test_replace_credentials_invalidates_the_pool_and_resets_status(onboarded) -> None:
    service, audit, _pool, activated, password = onboarded
    _connection, runtime_before = await service.active_connection_runtime(workspace_id=WORKSPACE)

    updated = await service.replace_credentials(
        workspace_id=WORKSPACE, data_source_id=activated.id, password=password, actor_user_id=uuid.uuid4(),
    )

    assert updated.status == "pending"
    assert updated.version == activated.version + 1
    # The pooled runtime built for the old credentials is disposed, not left
    # dangling -- its underlying engine is torn down by invalidate().
    assert runtime_before.database._engine is None
    entries = await audit.list_for_workspace(workspace_id=WORKSPACE)
    assert any(entry.event_type == "datasource_credentials_replaced" for entry in entries)
    # The connection is no longer "active" (reset to pending), so a caller
    # asking for the active connection again correctly finds none until
    # it's re-verified and re-activated.
    with pytest.raises(DataSourceOnboardingError):
        await service.active_connection_runtime(workspace_id=WORKSPACE)


@pytest.mark.asyncio
async def test_update_configuration_changing_connection_details_bumps_version_and_pool_key(onboarded) -> None:
    service, audit, pool, activated, _password = onboarded
    await service.active_connection_runtime(workspace_id=WORKSPACE)

    new_config = activated.config.model_copy(update={"statement_timeout_seconds": 30})
    updated = await service.update_configuration(
        workspace_id=WORKSPACE, data_source_id=activated.id, config=new_config, actor_user_id=uuid.uuid4(),
    )

    assert updated.version == activated.version + 1
    assert updated.status == "pending"
    entries = await audit.list_for_workspace(workspace_id=WORKSPACE)
    assert any(entry.event_type == "datasource_configuration_updated" for entry in entries)
    # The old pooled runtime was invalidated -- nothing is cached for this
    # data source under any version anymore.
    assert not any(key[1] == activated.id for key in pool._entries)


@pytest.mark.asyncio
async def test_disable_removes_visibility_from_active_connection_runtime(onboarded) -> None:
    service, audit, pool, activated, _password = onboarded
    await service.active_connection_runtime(workspace_id=WORKSPACE)

    disabled = await service.disable(workspace_id=WORKSPACE, data_source_id=activated.id, actor_user_id=uuid.uuid4())

    assert disabled.status == "disabled"
    with pytest.raises(DataSourceOnboardingError):
        await service.active_connection_runtime(workspace_id=WORKSPACE)
    assert not any(key[1] == activated.id for key in pool._entries)
    entries = await audit.list_for_workspace(workspace_id=WORKSPACE)
    assert any(entry.event_type == "datasource_disabled" for entry in entries)


@pytest.mark.asyncio
async def test_enable_requires_the_connection_to_currently_be_disabled(onboarded) -> None:
    service, _audit, _pool, activated, _password = onboarded

    with pytest.raises(DataSourceStateError):
        await service.enable(workspace_id=WORKSPACE, data_source_id=activated.id)

    await service.disable(workspace_id=WORKSPACE, data_source_id=activated.id)
    enabled = await service.enable(workspace_id=WORKSPACE, data_source_id=activated.id, actor_user_id=uuid.uuid4())
    assert enabled.status == "pending"


@pytest.mark.asyncio
async def test_soft_delete_makes_the_connection_invisible_to_every_other_method(onboarded) -> None:
    service, audit, pool, activated, _password = onboarded

    deleted = await service.soft_delete(workspace_id=WORKSPACE, data_source_id=activated.id, actor_user_id=uuid.uuid4())

    assert deleted.status == "deleted"
    assert deleted.deleted_at is not None
    fetched = await service._store.get_connection(workspace_id=WORKSPACE, data_source_id=activated.id)
    assert fetched is None
    items, _total = await service._store.list_connections(workspace_id=WORKSPACE, status=None, limit=10, offset=0)
    assert activated.id not in [item.id for item in items]
    assert not any(key[1] == activated.id for key in pool._entries)
    entries = await audit.list_for_workspace(workspace_id=WORKSPACE)
    assert any(entry.event_type == "datasource_deleted" for entry in entries)

    with pytest.raises(DataSourceOnboardingError):
        await service.test_connectivity(workspace_id=WORKSPACE, data_source_id=activated.id)
