"""The full 9-step onboarding flow, end to end, against real PostgreSQL.

Exercises DataSourceOnboardingService against a throwaway, genuinely
restricted role connecting back to the same database this test suite already
runs in -- real tables (conversations/messages/agent_runs), a real encrypted
password round trip, a real SSL-enabled connection, and a real live-probe
read-only verification. Nothing here is mocked.

Skips when TEST_DATABASE_URL is unset, like the other database tests.

Every test here needs exactly one valid workspace to satisfy
``data_sources.workspace_id``'s foreign key, so this file reuses the
always-present legacy workspace row seeded by migration
``20260903_0016_create_legacy_workspace.py`` (fixed id
``00000000-0000-0000-0000-000000000001``) rather than minting its own --
no other test in this suite touches ``data_sources`` under that workspace,
so purging by that workspace id here cannot collide with another file's
fixtures.
"""

from __future__ import annotations

import os
import uuid
from datetime import timedelta
from uuid import UUID

import pytest
from cryptography.fernet import Fernet
from pytest_asyncio import fixture
from sqlalchemy import delete, text
from sqlalchemy.engine import make_url

pytest.importorskip("sqlalchemy")

from app.datasources.contracts import DataSourceConnectionConfig
from app.datasources.encryption import FernetSecretCipher
from app.datasources.service import DataSourceConnectionRefusedError, DataSourceOnboardingError, DataSourceOnboardingService
from app.datasources.store import PostgresDataSourceStore
from app.db.records import DataSourceColumnRecord, DataSourceRecord, DataSourceRelationshipRecord, DataSourceTableRecord
from app.db.session import Database
from app.security.credentials import CredentialProvider, SecretReference

pytestmark = pytest.mark.postgres

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
#: The fixed legacy workspace id seeded by migration 20260903_0016 -- always
#: present, so reusable here without minting or cleaning up a workspace row.
WORKSPACE: UUID = UUID("00000000-0000-0000-0000-000000000001")


class _FixedCredentialProvider(CredentialProvider):
    def __init__(self, value: str) -> None:
        self._value = value

    def resolve(self, reference: SecretReference) -> str | None:
        return self._value


async def _purge() -> None:
    database = Database(TEST_DATABASE_URL or "")
    try:
        async with database.session() as session:
            async with session.begin():
                from sqlalchemy import select

                source_ids = (await session.scalars(
                    select(DataSourceRecord.id).where(DataSourceRecord.workspace_id == WORKSPACE)
                )).all()
                if source_ids:
                    await session.execute(
                        delete(DataSourceRelationshipRecord).where(DataSourceRelationshipRecord.data_source_id.in_(source_ids))
                    )
                    table_ids = (await session.scalars(
                        select(DataSourceTableRecord.id).where(DataSourceTableRecord.data_source_id.in_(source_ids))
                    )).all()
                    if table_ids:
                        await session.execute(
                            delete(DataSourceColumnRecord).where(DataSourceColumnRecord.data_source_table_id.in_(table_ids))
                        )
                    await session.execute(delete(DataSourceTableRecord).where(DataSourceTableRecord.data_source_id.in_(source_ids)))
                await session.execute(delete(DataSourceRecord).where(DataSourceRecord.workspace_id == WORKSPACE))
    finally:
        await database.dispose()


@fixture
async def admin_dsn():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    yield TEST_DATABASE_URL


@fixture
async def restricted_role(admin_dsn):
    """A throwaway, genuinely read-only role with SELECT on this test database's own tables."""

    url = make_url(admin_dsn)
    role_name = f"datasource_svc_ro_{uuid.uuid4().hex[:12]}"
    password = "test-onboarding-password"
    admin = Database(admin_dsn)
    try:
        async with admin.session() as session:
            async with session.begin():
                await session.execute(text(
                    f'CREATE ROLE "{role_name}" LOGIN PASSWORD $${password}$$ '
                    "NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS"
                ))
                await session.execute(text(f'GRANT CONNECT ON DATABASE "{url.database}" TO "{role_name}"'))
                await session.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role_name}"'))
                await session.execute(text(f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{role_name}"'))
        yield url, role_name, password
    finally:
        async with admin.session() as session:
            async with session.begin():
                await session.execute(text(f'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM "{role_name}"'))
                await session.execute(text(f'REVOKE ALL ON SCHEMA public FROM "{role_name}"'))
                await session.execute(text(f'REVOKE CONNECT ON DATABASE "{url.database}" FROM "{role_name}"'))
                await session.execute(text(f'DROP ROLE "{role_name}"'))
        await admin.dispose()


@fixture
async def service(admin_dsn):
    await _purge()
    database = Database(TEST_DATABASE_URL)
    cipher = FernetSecretCipher(_FixedCredentialProvider(Fernet.generate_key().decode()))
    store = PostgresDataSourceStore(database)
    try:
        yield DataSourceOnboardingService(
            store=store, cipher=cipher, allow_local_hosts=True,
            freshness_stale_after=timedelta(hours=48),
        )
    finally:
        await database.dispose()
        await _purge()


def _config(url) -> DataSourceConnectionConfig:
    return DataSourceConnectionConfig(
        host=url.host or "localhost", port=url.port or 5432, database=url.database,
        username="placeholder", allowed_schemas=["public"], ssl_mode="require",
    )


@pytest.mark.asyncio
async def test_the_full_onboarding_flow_reaches_activation(service, restricted_role) -> None:
    url, role_name, password = restricted_role
    connection = await service.create_connection(
        workspace_id=WORKSPACE, name="Primary Analytics",
        config=_config(url).model_copy(update={"username": role_name}), password=password,
    )
    assert connection.status == "pending"

    test_result = await service.test_connectivity(workspace_id=WORKSPACE, data_source_id=connection.id)
    assert test_result.success is True

    verification = await service.verify_read_only_behavior(workspace_id=WORKSPACE, data_source_id=connection.id)
    assert verification.is_read_only is True
    assert verification.role_is_superuser is False

    schemas = await service.list_accessible_schemas(workspace_id=WORKSPACE, data_source_id=connection.id)
    assert "conversations" in [table.name for table in schemas.tables]

    table = await service.select_and_profile_table(
        workspace_id=WORKSPACE, data_source_id=connection.id, schema_name="public",
        technical_name="conversations", business_name="Conversations",
        description="One row per agent conversation", freshness_column="updated_at",
    )
    assert table.approved_by is None
    assert {column.technical_name for column in table.columns} == {"id", "title", "created_at", "updated_at", "workspace_id"}
    assert "updated_at" in table.time_columns

    relationships = await service.discover_table_relationships(workspace_id=WORKSPACE, data_source_id=connection.id)
    # "conversations" carries a real FK to "workspaces" (the tenant-isolation
    # migration) -- discovered even though "workspaces" itself was never
    # selected/catalogued; only actual *approval* of a relationship depends
    # on both sides being catalogued, not discovery.
    assert len(relationships) == 1
    assert relationships[0].source_table == "conversations"
    assert relationships[0].source_column == "workspace_id"
    assert relationships[0].target_table == "workspaces"
    assert relationships[0].discovery_method == "foreign_key"

    with pytest.raises(DataSourceOnboardingError, match="approved"):
        await service.activate(workspace_id=WORKSPACE, data_source_id=connection.id)

    from app.datasources.store import PostgresDataSourceStore

    store = service._store
    assert isinstance(store, PostgresDataSourceStore)
    await store.approve_table(workspace_id=WORKSPACE, data_source_id=connection.id, table_id=table.id, approved_by="alice")

    activated = await service.activate(workspace_id=WORKSPACE, data_source_id=connection.id)
    assert activated.status == "active"

    freshness = await service.check_freshness(workspace_id=WORKSPACE, data_source_id=connection.id)
    assert freshness.stale is False
    assert freshness.latest_source_timestamp is not None
    assert "conversations" in freshness.per_table


@pytest.mark.asyncio
async def test_a_writable_role_fails_verification_and_is_recorded(service, admin_dsn) -> None:
    url = make_url(admin_dsn)
    connection = await service.create_connection(
        workspace_id=WORKSPACE, name="Writable by mistake",
        config=_config(url).model_copy(update={"username": url.username}), password=url.password or "",
    )

    verification = await service.verify_read_only_behavior(workspace_id=WORKSPACE, data_source_id=connection.id)

    assert verification.is_read_only is False
    fetched = await service._store.get_connection(workspace_id=WORKSPACE, data_source_id=connection.id)
    assert fetched.status == "failed"
    assert fetched.health_status == "unreachable"


@pytest.mark.asyncio
async def test_activation_before_read_only_verification_is_refused(service, restricted_role) -> None:
    url, role_name, password = restricted_role
    connection = await service.create_connection(
        workspace_id=WORKSPACE, name="Not yet verified",
        config=_config(url).model_copy(update={"username": role_name}), password=password,
    )

    with pytest.raises(DataSourceOnboardingError, match="read-only verification"):
        await service.activate(workspace_id=WORKSPACE, data_source_id=connection.id)


@pytest.mark.asyncio
async def test_a_host_resolving_to_a_private_address_is_refused_unless_allowed(admin_dsn, restricted_role) -> None:
    """The service-level allow_local_hosts flag, not just the bare security helper, gates this."""

    url, role_name, password = restricted_role
    await _purge()
    database = Database(TEST_DATABASE_URL)
    cipher = FernetSecretCipher(_FixedCredentialProvider(Fernet.generate_key().decode()))
    store = PostgresDataSourceStore(database)
    strict_service = DataSourceOnboardingService(store=store, cipher=cipher, allow_local_hosts=False)
    try:
        connection = await strict_service.create_connection(
            workspace_id=WORKSPACE, name="Should be refused",
            config=_config(url).model_copy(update={"username": role_name}), password=password,
        )

        with pytest.raises(DataSourceConnectionRefusedError):
            await strict_service.test_connectivity(workspace_id=WORKSPACE, data_source_id=connection.id)

        fetched = await store.get_connection(workspace_id=WORKSPACE, data_source_id=connection.id)
        assert fetched.status == "failed"
        assert fetched.health_status == "unreachable"
    finally:
        await database.dispose()
        await _purge()


@pytest.mark.asyncio
async def test_cross_workspace_access_is_refused(service, restricted_role) -> None:
    url, role_name, password = restricted_role
    connection = await service.create_connection(
        workspace_id=WORKSPACE, name="Isolated",
        config=_config(url).model_copy(update={"username": role_name}), password=password,
    )

    with pytest.raises(DataSourceOnboardingError, match="not found"):
        await service.test_connectivity(workspace_id=uuid.uuid4(), data_source_id=connection.id)
