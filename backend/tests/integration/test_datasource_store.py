"""Data source connection and catalog persistence, against a real database.

Skips when TEST_DATABASE_URL is unset, like the other database tests. Rows
are scoped to workspaces named ``test-datasources-*`` and purged on the way
in and out.
"""

from __future__ import annotations

import os

import pytest
from pytest_asyncio import fixture
from sqlalchemy import delete, select

pytest.importorskip("sqlalchemy")

from app.datasources.contracts import DataSourceConnectionConfig, RelationshipCandidate
from app.datasources.store import (
    ColumnInput,
    DataSourceNotFoundError,
    DataSourceRelationshipNotFoundError,
    DataSourceStore,
    DataSourceTableNotFoundError,
    PostgresDataSourceStore,
)
from app.db.records import DataSourceColumnRecord, DataSourceRecord, DataSourceRelationshipRecord, DataSourceTableRecord
from app.db.session import Database

pytestmark = pytest.mark.postgres

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
WORKSPACE_A = "test-datasources-a"
WORKSPACE_B = "test-datasources-b"


async def _purge() -> None:
    database = Database(TEST_DATABASE_URL or "")
    try:
        async with database.session() as session:
            async with session.begin():
                source_ids = (await session.scalars(
                    select(DataSourceRecord.id).where(DataSourceRecord.workspace_id.in_([WORKSPACE_A, WORKSPACE_B]))
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
                await session.execute(delete(DataSourceRecord).where(DataSourceRecord.workspace_id.in_([WORKSPACE_A, WORKSPACE_B])))
    finally:
        await database.dispose()


@fixture
async def store():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    await _purge()
    database = Database(TEST_DATABASE_URL)
    try:
        yield PostgresDataSourceStore(database)
    finally:
        await database.dispose()
        await _purge()


def _config(**overrides) -> DataSourceConnectionConfig:
    fields = dict(host="db.example.com", database="analytics", username="ro_user", allowed_schemas=["public"])
    fields.update(overrides)
    return DataSourceConnectionConfig(**fields)


async def _connection(store: DataSourceStore, *, workspace_id: str = WORKSPACE_A, **overrides):
    return await store.create_connection(
        workspace_id=workspace_id, name=overrides.pop("name", "Primary Analytics"),
        config=overrides.pop("config", _config()), encrypted_password=overrides.pop("encrypted_password", "ciphertext"),
    )


@pytest.mark.asyncio
async def test_a_created_connection_round_trips_every_field_except_the_password(store) -> None:
    connection = await _connection(store)

    fetched = await store.get_connection(workspace_id=WORKSPACE_A, data_source_id=connection.id)

    assert fetched is not None
    assert fetched.config.host == "db.example.com"
    assert fetched.status == "pending"
    assert fetched.health_status == "unknown"
    assert "encrypted_password" not in fetched.model_dump()


@pytest.mark.asyncio
async def test_get_encrypted_password_is_the_only_way_to_read_it_back(store) -> None:
    connection = await _connection(store, encrypted_password="the-ciphertext")

    password = await store.get_encrypted_password(workspace_id=WORKSPACE_A, data_source_id=connection.id)

    assert password == "the-ciphertext"


@pytest.mark.asyncio
async def test_a_connection_from_another_workspace_is_invisible(store) -> None:
    connection = await _connection(store, workspace_id=WORKSPACE_A)

    assert await store.get_connection(workspace_id=WORKSPACE_B, data_source_id=connection.id) is None
    assert await store.get_encrypted_password(workspace_id=WORKSPACE_B, data_source_id=connection.id) is None


@pytest.mark.asyncio
async def test_listing_is_scoped_to_its_workspace(store) -> None:
    await _connection(store, workspace_id=WORKSPACE_A, name="A's source")
    await _connection(store, workspace_id=WORKSPACE_B, name="B's source")

    items_a, total_a = await store.list_connections(workspace_id=WORKSPACE_A, status=None, limit=30, offset=0)
    items_b, total_b = await store.list_connections(workspace_id=WORKSPACE_B, status=None, limit=30, offset=0)

    assert total_a == 1 and items_a[0].name == "A's source"
    assert total_b == 1 and items_b[0].name == "B's source"


@pytest.mark.asyncio
async def test_update_connection_status_records_test_results(store) -> None:
    connection = await _connection(store)

    updated = await store.update_connection_status(
        workspace_id=WORKSPACE_A, data_source_id=connection.id, status="verified_read_only",
        health_status="healthy",
    )

    assert updated.status == "verified_read_only"
    assert updated.health_status == "healthy"


@pytest.mark.asyncio
async def test_update_connection_status_across_workspaces_is_refused(store) -> None:
    connection = await _connection(store, workspace_id=WORKSPACE_A)

    with pytest.raises(DataSourceNotFoundError):
        await store.update_connection_status(workspace_id=WORKSPACE_B, data_source_id=connection.id, status="active")


@pytest.mark.asyncio
async def test_changing_config_resets_status_to_pending(store) -> None:
    connection = await _connection(store)
    await store.update_connection_status(workspace_id=WORKSPACE_A, data_source_id=connection.id, status="active")

    updated = await store.update_connection_config(
        workspace_id=WORKSPACE_A, data_source_id=connection.id, changes={"config": _config(host="new-host.example.com")},
    )

    assert updated.config.host == "new-host.example.com"
    assert updated.status == "pending"


@pytest.mark.asyncio
async def test_upsert_table_creates_a_table_with_its_columns(store) -> None:
    connection = await _connection(store)

    table = await store.upsert_table(
        workspace_id=WORKSPACE_A, data_source_id=connection.id, schema_name="public", technical_name="orders",
        business_name="Orders", description="One row per order", grain="order", freshness_column="updated_at",
        columns=[
            ColumnInput(technical_name="id", data_type="uuid", role="primary_key"),
            ColumnInput(technical_name="email", data_type="text", role="dimension", sensitivity="personal_data"),
            ColumnInput(technical_name="total", data_type="numeric", role="measure", example_values=["9.99"]),
        ],
    )

    assert table.business_name == "Orders"
    assert table.primary_key == ["id"]
    assert table.dimensions == ["email"]
    assert table.measures == ["total"]
    assert table.sensitive_columns == ["email"]
    assert table.approved_by is None


@pytest.mark.asyncio
async def test_correcting_a_table_resets_its_approval(store) -> None:
    connection = await _connection(store)
    table = await store.upsert_table(
        workspace_id=WORKSPACE_A, data_source_id=connection.id, schema_name="public", technical_name="orders",
        business_name="Orders", description=None, grain=None, freshness_column=None,
        columns=[ColumnInput(technical_name="id", data_type="uuid", role="primary_key")],
    )
    await store.approve_table(workspace_id=WORKSPACE_A, data_source_id=connection.id, table_id=table.id, approved_by="alice")

    corrected = await store.upsert_table(
        workspace_id=WORKSPACE_A, data_source_id=connection.id, schema_name="public", technical_name="orders",
        business_name="Customer Orders", description="corrected", grain=None, freshness_column=None,
        columns=[ColumnInput(technical_name="id", data_type="uuid", role="primary_key")],
    )

    assert corrected.business_name == "Customer Orders"
    assert corrected.approved_by is None
    assert corrected.approved_at is None


@pytest.mark.asyncio
async def test_upsert_table_across_workspaces_is_refused(store) -> None:
    connection = await _connection(store, workspace_id=WORKSPACE_A)

    with pytest.raises(DataSourceNotFoundError):
        await store.upsert_table(
            workspace_id=WORKSPACE_B, data_source_id=connection.id, schema_name="public", technical_name="orders",
            business_name="Orders", description=None, grain=None, freshness_column=None,
            columns=[ColumnInput(technical_name="id", data_type="uuid", role="primary_key")],
        )


@pytest.mark.asyncio
async def test_set_table_active_toggles_exclusion(store) -> None:
    connection = await _connection(store)
    table = await store.upsert_table(
        workspace_id=WORKSPACE_A, data_source_id=connection.id, schema_name="public", technical_name="orders",
        business_name="Orders", description=None, grain=None, freshness_column=None,
        columns=[ColumnInput(technical_name="id", data_type="uuid", role="primary_key")],
    )

    deactivated = await store.set_table_active(workspace_id=WORKSPACE_A, data_source_id=connection.id, table_id=table.id, active=False)
    assert deactivated.active is False

    active_only, _total = (
        await store.list_tables(workspace_id=WORKSPACE_A, data_source_id=connection.id, active_only=True), None,
    )
    assert active_only == []


@pytest.mark.asyncio
async def test_set_table_active_for_an_unknown_table_is_refused(store) -> None:
    connection = await _connection(store)
    from uuid import uuid4

    with pytest.raises(DataSourceTableNotFoundError):
        await store.set_table_active(workspace_id=WORKSPACE_A, data_source_id=connection.id, table_id=uuid4(), active=False)


@pytest.mark.asyncio
async def test_approve_table_stamps_who_and_when(store) -> None:
    connection = await _connection(store)
    table = await store.upsert_table(
        workspace_id=WORKSPACE_A, data_source_id=connection.id, schema_name="public", technical_name="orders",
        business_name="Orders", description=None, grain=None, freshness_column=None,
        columns=[ColumnInput(technical_name="id", data_type="uuid", role="primary_key")],
    )

    approved = await store.approve_table(workspace_id=WORKSPACE_A, data_source_id=connection.id, table_id=table.id, approved_by="alice")

    assert approved.approved_by == "alice"
    assert approved.approved_at is not None


@pytest.mark.asyncio
async def test_list_tables_for_an_unknown_connection_returns_none(store) -> None:
    from uuid import uuid4

    result = await store.list_tables(workspace_id=WORKSPACE_A, data_source_id=uuid4(), active_only=False)

    assert result is None


@pytest.mark.asyncio
async def test_relationship_candidates_start_pending(store) -> None:
    connection = await _connection(store)

    created = await store.create_relationship_candidates(
        workspace_id=WORKSPACE_A, data_source_id=connection.id,
        candidates=[
            RelationshipCandidate(
                source_table="orders", source_column="customer_id", target_table="customers", target_column="id",
                cardinality="many_to_one", confidence=1.0, discovery_method="foreign_key",
            ),
            RelationshipCandidate(
                source_table="orders", source_column="promo_code", target_table="promotions", target_column="code",
                cardinality="many_to_one", confidence=0.4, discovery_method="inferred",
            ),
        ],
    )

    assert len(created) == 2
    assert all(item.approval_status == "pending" for item in created)


@pytest.mark.asyncio
async def test_approving_a_relationship_excludes_it_from_the_pending_list(store) -> None:
    connection = await _connection(store)
    [relationship] = await store.create_relationship_candidates(
        workspace_id=WORKSPACE_A, data_source_id=connection.id,
        candidates=[RelationshipCandidate(
            source_table="orders", source_column="customer_id", target_table="customers", target_column="id",
            cardinality="many_to_one", confidence=1.0, discovery_method="foreign_key",
        )],
    )

    await store.set_relationship_approval(
        workspace_id=WORKSPACE_A, data_source_id=connection.id, relationship_id=relationship.id,
        approval_status="approved", approved_by="alice",
    )

    approved_only = await store.list_relationships(workspace_id=WORKSPACE_A, data_source_id=connection.id, approval_status="approved")
    pending_only = await store.list_relationships(workspace_id=WORKSPACE_A, data_source_id=connection.id, approval_status="pending")
    assert len(approved_only) == 1
    assert pending_only == []


@pytest.mark.asyncio
async def test_rejecting_a_relationship_clears_approver_fields(store) -> None:
    connection = await _connection(store)
    [relationship] = await store.create_relationship_candidates(
        workspace_id=WORKSPACE_A, data_source_id=connection.id,
        candidates=[RelationshipCandidate(
            source_table="orders", source_column="customer_id", target_table="customers", target_column="id",
            cardinality="many_to_one", confidence=1.0, discovery_method="foreign_key",
        )],
    )
    await store.set_relationship_approval(
        workspace_id=WORKSPACE_A, data_source_id=connection.id, relationship_id=relationship.id,
        approval_status="approved", approved_by="alice",
    )

    rejected = await store.set_relationship_approval(
        workspace_id=WORKSPACE_A, data_source_id=connection.id, relationship_id=relationship.id,
        approval_status="rejected", approved_by=None,
    )

    assert rejected.approval_status == "rejected"
    assert rejected.approved_by is None
    assert rejected.approved_at is None


@pytest.mark.asyncio
async def test_set_relationship_approval_for_an_unknown_relationship_is_refused(store) -> None:
    connection = await _connection(store)
    from uuid import uuid4

    with pytest.raises(DataSourceRelationshipNotFoundError):
        await store.set_relationship_approval(
            workspace_id=WORKSPACE_A, data_source_id=connection.id, relationship_id=uuid4(),
            approval_status="approved", approved_by="alice",
        )


@pytest.mark.asyncio
async def test_list_relationships_for_an_unknown_connection_returns_none(store) -> None:
    from uuid import uuid4

    result = await store.list_relationships(workspace_id=WORKSPACE_A, data_source_id=uuid4())

    assert result is None
