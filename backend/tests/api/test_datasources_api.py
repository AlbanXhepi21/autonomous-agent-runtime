"""The data source onboarding HTTP surface: request/response shape and error codes.

In-process fakes stand in for PostgreSQL and for the live-connection parts of
DataSourceOnboardingService (SSL/SSRF checks, an actual socket, live
profiling) -- those are already proven for real in
tests/integration/test_datasource_store.py,
tests/integration/test_datasource_connectivity.py, and
tests/integration/test_datasource_onboarding_service.py. This suite is only
about the API contract: status codes, error envelopes, that a password is
never present in any response, and that catalog/relationship governance
(approval resets, activation gating) is reachable end to end through routes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.analytics.schema.contracts import DatabaseSchemaSummary, DatabaseTable
from app.api.routes.datasources import router
from app.composition import get_data_source_onboarding_service, get_data_source_store
from app.datasources.contracts import (
    ConnectionTestResult,
    DataSourceColumnCatalogEntry,
    DataSourceConnection,
    DataSourceRelationship,
    DataSourceStatus,
    DataSourceTableCatalogEntry,
    FreshnessSnapshot,
    HealthStatus,
    ReadOnlyVerification,
    RelationshipApprovalStatus,
    RelationshipCandidate,
)
from app.datasources.service import DataSourceConnectionRefusedError, DataSourceOnboardingError
from app.datasources.store import (
    ColumnInput,
    DataSourceNotFoundError,
    DataSourceRelationshipNotFoundError,
    DataSourceTableNotFoundError,
)

WORKSPACE_A = "workspace-a"
WORKSPACE_B = "workspace-b"


def _now() -> datetime:
    return datetime.now(UTC)


def _column_from_input(item: ColumnInput) -> DataSourceColumnCatalogEntry:
    return DataSourceColumnCatalogEntry(
        id=uuid4(), table_id=uuid4(), technical_name=item.technical_name, data_type=item.data_type,
        role=item.role, sensitivity=item.sensitivity, excluded=item.excluded, example_values=item.example_values,
    )


@dataclass
class FakeDataSourceStore:
    """Everything DataSourceStore promises, in memory -- no PostgreSQL involved."""

    connections: dict[UUID, DataSourceConnection] = field(default_factory=dict)
    passwords: dict[UUID, str] = field(default_factory=dict)
    tables: dict[UUID, DataSourceTableCatalogEntry] = field(default_factory=dict)
    relationships: dict[UUID, DataSourceRelationship] = field(default_factory=dict)

    async def create_connection(self, *, workspace_id, name, config, encrypted_password) -> DataSourceConnection:
        now = _now()
        connection = DataSourceConnection(
            id=uuid4(), workspace_id=workspace_id, name=name, config=config,
            status="pending", health_status="unknown", created_at=now, updated_at=now,
        )
        self.connections[connection.id] = connection
        self.passwords[connection.id] = encrypted_password
        return connection

    async def get_connection(self, *, workspace_id, data_source_id) -> DataSourceConnection | None:
        item = self.connections.get(data_source_id)
        return item if item is not None and item.workspace_id == workspace_id else None

    async def get_encrypted_password(self, *, workspace_id, data_source_id) -> str | None:
        connection = await self.get_connection(workspace_id=workspace_id, data_source_id=data_source_id)
        return None if connection is None else self.passwords.get(data_source_id)

    async def list_connections(self, *, workspace_id, status, limit, offset):
        items = [item for item in self.connections.values() if item.workspace_id == workspace_id]
        if status is not None:
            items = [item for item in items if item.status == status]
        return items[offset:offset + limit], len(items)

    async def update_connection_status(
        self, *, workspace_id, data_source_id, status: DataSourceStatus | None = None,
        health_status: HealthStatus | None = None, last_connection_at=None, last_connection_error=None,
        last_profiled_at=None,
    ) -> DataSourceConnection:
        existing = self.connections.get(data_source_id)
        if existing is None or existing.workspace_id != workspace_id:
            raise DataSourceNotFoundError(str(data_source_id))
        updated = existing.model_copy(update={
            key: value for key, value in {
                "status": status, "health_status": health_status, "last_connection_at": last_connection_at,
                "last_connection_error": last_connection_error, "last_profiled_at": last_profiled_at,
                "updated_at": _now(),
            }.items() if value is not None or key == "updated_at"
        })
        self.connections[data_source_id] = updated
        return updated

    async def update_connection_config(self, *, workspace_id, data_source_id, changes: dict[str, Any]) -> DataSourceConnection:
        existing = self.connections.get(data_source_id)
        if existing is None or existing.workspace_id != workspace_id:
            raise DataSourceNotFoundError(str(data_source_id))
        payload = {"updated_at": _now(), "status": "pending"}
        payload.update(changes)
        updated = existing.model_copy(update=payload)
        self.connections[data_source_id] = updated
        return updated

    async def upsert_table(
        self, *, workspace_id, data_source_id, schema_name, technical_name, business_name, description,
        grain, freshness_column, columns: list[ColumnInput],
    ) -> DataSourceTableCatalogEntry:
        connection = self.connections.get(data_source_id)
        if connection is None or connection.workspace_id != workspace_id:
            raise DataSourceNotFoundError(str(data_source_id))
        existing = next(
            (t for t in self.tables.values()
             if t.data_source_id == data_source_id and t.schema_name == schema_name and t.technical_name == technical_name),
            None,
        )
        now = _now()
        table = DataSourceTableCatalogEntry(
            id=existing.id if existing else uuid4(), data_source_id=data_source_id, schema_name=schema_name,
            technical_name=technical_name, business_name=business_name, description=description, grain=grain,
            freshness_column=freshness_column, active=existing.active if existing else True,
            approved_by=None, approved_at=None, columns=[_column_from_input(item) for item in columns],
            created_at=existing.created_at if existing else now, updated_at=now,
        )
        self.tables[table.id] = table
        return table

    async def get_table(self, *, workspace_id, data_source_id, table_id) -> DataSourceTableCatalogEntry | None:
        connection = self.connections.get(data_source_id)
        if connection is None or connection.workspace_id != workspace_id:
            return None
        table = self.tables.get(table_id)
        return table if table is not None and table.data_source_id == data_source_id else None

    async def list_tables(self, *, workspace_id, data_source_id, active_only=False):
        connection = self.connections.get(data_source_id)
        if connection is None or connection.workspace_id != workspace_id:
            return None
        items = [t for t in self.tables.values() if t.data_source_id == data_source_id]
        if active_only:
            items = [t for t in items if t.active]
        return items

    async def set_table_active(self, *, workspace_id, data_source_id, table_id, active) -> DataSourceTableCatalogEntry:
        connection = self.connections.get(data_source_id)
        if connection is None or connection.workspace_id != workspace_id:
            raise DataSourceNotFoundError(str(data_source_id))
        table = self.tables.get(table_id)
        if table is None or table.data_source_id != data_source_id:
            raise DataSourceTableNotFoundError(str(table_id))
        updated = table.model_copy(update={"active": active, "updated_at": _now()})
        self.tables[table_id] = updated
        return updated

    async def approve_table(self, *, workspace_id, data_source_id, table_id, approved_by) -> DataSourceTableCatalogEntry:
        connection = self.connections.get(data_source_id)
        if connection is None or connection.workspace_id != workspace_id:
            raise DataSourceNotFoundError(str(data_source_id))
        table = self.tables.get(table_id)
        if table is None or table.data_source_id != data_source_id:
            raise DataSourceTableNotFoundError(str(table_id))
        now = _now()
        updated = table.model_copy(update={"approved_by": approved_by, "approved_at": now, "updated_at": now})
        self.tables[table_id] = updated
        return updated

    async def create_relationship_candidates(
        self, *, workspace_id, data_source_id, candidates: list[RelationshipCandidate],
    ) -> list[DataSourceRelationship]:
        connection = self.connections.get(data_source_id)
        if connection is None or connection.workspace_id != workspace_id:
            raise DataSourceNotFoundError(str(data_source_id))
        now = _now()
        created = []
        for candidate in candidates:
            relationship = DataSourceRelationship(
                id=uuid4(), data_source_id=data_source_id, source_table=candidate.source_table,
                source_column=candidate.source_column, target_table=candidate.target_table,
                target_column=candidate.target_column, cardinality=candidate.cardinality,
                confidence=candidate.confidence, discovery_method=candidate.discovery_method,
                approval_status="pending", created_at=now, updated_at=now,
            )
            self.relationships[relationship.id] = relationship
            created.append(relationship)
        return created

    async def list_relationships(self, *, workspace_id, data_source_id, approval_status: RelationshipApprovalStatus | None = None):
        connection = self.connections.get(data_source_id)
        if connection is None or connection.workspace_id != workspace_id:
            return None
        items = [r for r in self.relationships.values() if r.data_source_id == data_source_id]
        if approval_status is not None:
            items = [r for r in items if r.approval_status == approval_status]
        return items

    async def set_relationship_approval(
        self, *, workspace_id, data_source_id, relationship_id, approval_status, approved_by,
    ) -> DataSourceRelationship:
        connection = self.connections.get(data_source_id)
        if connection is None or connection.workspace_id != workspace_id:
            raise DataSourceNotFoundError(str(data_source_id))
        relationship = self.relationships.get(relationship_id)
        if relationship is None or relationship.data_source_id != data_source_id:
            raise DataSourceRelationshipNotFoundError(str(relationship_id))
        now = _now()
        updated = relationship.model_copy(update={
            "approval_status": approval_status,
            "approved_by": approved_by if approval_status == "approved" else None,
            "approved_at": now if approval_status == "approved" else None,
            "updated_at": now,
        })
        self.relationships[relationship_id] = updated
        return updated


@dataclass
class FakeOnboardingService:
    """Mirrors DataSourceOnboardingService's public steps without a live connection.

    ``refuse`` simulates a security guard rejecting a connection (the real
    service's DataSourceConnectionRefusedError path) so the API's 422
    handling can be proven without a real socket.
    """

    store: FakeDataSourceStore
    refuse: bool = False

    async def create_connection(self, *, workspace_id, name, config, password) -> DataSourceConnection:
        return await self.store.create_connection(
            workspace_id=workspace_id, name=name, config=config, encrypted_password=f"encrypted:{password}",
        )

    async def _guard(self, *, workspace_id, data_source_id) -> DataSourceConnection:
        connection = await self.store.get_connection(workspace_id=workspace_id, data_source_id=data_source_id)
        if connection is None:
            raise DataSourceOnboardingError("Data source not found.")
        if self.refuse:
            await self.store.update_connection_status(
                workspace_id=workspace_id, data_source_id=data_source_id, status="failed",
                health_status="unreachable", last_connection_at=_now(), last_connection_error="refused",
            )
            raise DataSourceConnectionRefusedError("Host resolves to a private address.")
        return connection

    async def test_connectivity(self, *, workspace_id, data_source_id) -> ConnectionTestResult:
        await self._guard(workspace_id=workspace_id, data_source_id=data_source_id)
        await self.store.update_connection_status(
            workspace_id=workspace_id, data_source_id=data_source_id, status="testing", last_connection_at=_now(),
        )
        return ConnectionTestResult(success=True, message="ok", server_version="PostgreSQL 16.0")

    async def verify_read_only_behavior(self, *, workspace_id, data_source_id) -> ReadOnlyVerification:
        await self._guard(workspace_id=workspace_id, data_source_id=data_source_id)
        await self.store.update_connection_status(
            workspace_id=workspace_id, data_source_id=data_source_id, status="verified_read_only",
            health_status="healthy", last_connection_at=_now(),
        )
        return ReadOnlyVerification(
            is_read_only=True, role_is_superuser=False, role_can_create_database=False,
            role_can_create_role=False, role_bypasses_row_level_security=False, message="read-only confirmed",
        )

    async def list_accessible_schemas(self, *, workspace_id, data_source_id) -> DatabaseSchemaSummary:
        await self._guard(workspace_id=workspace_id, data_source_id=data_source_id)
        return DatabaseSchemaSummary(
            schemas=["public"], tables=[DatabaseTable(name="orders", schema="public")],
        )

    async def select_and_profile_table(
        self, *, workspace_id, data_source_id, schema_name, technical_name, business_name,
        description=None, grain=None, freshness_column=None,
    ) -> DataSourceTableCatalogEntry:
        await self._guard(workspace_id=workspace_id, data_source_id=data_source_id)
        columns = [
            ColumnInput(technical_name="id", data_type="uuid", role="primary_key"),
            ColumnInput(technical_name="total", data_type="numeric", role="measure"),
        ]
        table = await self.store.upsert_table(
            workspace_id=workspace_id, data_source_id=data_source_id, schema_name=schema_name,
            technical_name=technical_name, business_name=business_name, description=description,
            grain=grain, freshness_column=freshness_column, columns=columns,
        )
        return table

    async def discover_table_relationships(self, *, workspace_id, data_source_id) -> list[DataSourceRelationship]:
        tables = await self.store.list_tables(workspace_id=workspace_id, data_source_id=data_source_id, active_only=True)
        if tables is None:
            raise DataSourceOnboardingError("Data source not found.")
        await self._guard(workspace_id=workspace_id, data_source_id=data_source_id)
        candidates = [
            RelationshipCandidate(
                source_table="orders", source_column="customer_id", target_table="customers", target_column="id",
                cardinality="many_to_one", confidence=1.0, discovery_method="foreign_key",
            )
        ]
        return await self.store.create_relationship_candidates(
            workspace_id=workspace_id, data_source_id=data_source_id, candidates=candidates,
        )

    async def activate(self, *, workspace_id, data_source_id) -> DataSourceConnection:
        connection = await self.store.get_connection(workspace_id=workspace_id, data_source_id=data_source_id)
        if connection is None:
            raise DataSourceOnboardingError("Data source not found.")
        if connection.status != "verified_read_only":
            raise DataSourceOnboardingError("A data source must pass read-only verification before it can be activated.")
        tables = await self.store.list_tables(workspace_id=workspace_id, data_source_id=data_source_id, active_only=True)
        if not tables or not any(table.approved_by for table in tables):
            raise DataSourceOnboardingError("At least one table must be reviewed and approved before activation.")
        return await self.store.update_connection_status(workspace_id=workspace_id, data_source_id=data_source_id, status="active")

    async def check_freshness(self, *, workspace_id, data_source_id) -> FreshnessSnapshot:
        tables = await self.store.list_tables(workspace_id=workspace_id, data_source_id=data_source_id, active_only=True)
        if tables is None:
            raise DataSourceOnboardingError("Data source not found.")
        await self._guard(workspace_id=workspace_id, data_source_id=data_source_id)
        return FreshnessSnapshot(
            data_source_id=data_source_id, checked_at=_now(), latest_source_timestamp=_now(),
            stale=False, health_status="healthy", per_table={},
        )


def _client(store: FakeDataSourceStore, service: FakeOnboardingService) -> TestClient:
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides = {
        get_data_source_store: lambda: store,
        get_data_source_onboarding_service: lambda: service,
    }
    return TestClient(application)


def _create_body(**overrides) -> dict:
    body = {
        "workspace_id": WORKSPACE_A, "name": "Primary Analytics", "host": "db.example.com",
        "database": "analytics", "username": "ro_user", "password": "super-secret",
        "allowed_schemas": ["public"],
    }
    body.update(overrides)
    return body


def test_create_returns_201_and_never_echoes_the_password() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))

    response = client.post("/api/v1/datasources", json=_create_body())

    assert response.status_code == 201
    body = response.json()
    assert body["host"] == "db.example.com"
    assert body["status"] == "pending"
    assert "password" not in body


def test_create_is_rejected_for_an_unsafe_ssl_mode() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))

    response = client.post("/api/v1/datasources", json=_create_body(ssl_mode="disable"))

    assert response.status_code == 422


def test_get_and_list_round_trip() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))
    created = client.post("/api/v1/datasources", json=_create_body()).json()

    fetched = client.get(f"/api/v1/datasources/{created['id']}", params={"workspace_id": WORKSPACE_A}).json()
    listed = client.get("/api/v1/datasources", params={"workspace_id": WORKSPACE_A}).json()

    assert fetched["id"] == created["id"]
    assert listed["total"] == 1


def test_get_is_404_across_workspaces() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))
    created = client.post("/api/v1/datasources", json=_create_body()).json()

    response = client.get(f"/api/v1/datasources/{created['id']}", params={"workspace_id": WORKSPACE_B})

    assert response.status_code == 404


def test_get_is_404_for_an_unknown_id() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))

    response = client.get(f"/api/v1/datasources/{uuid4()}", params={"workspace_id": WORKSPACE_A})

    assert response.status_code == 404


def test_test_connection_succeeds() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))
    created = client.post("/api/v1/datasources", json=_create_body()).json()

    response = client.post(f"/api/v1/datasources/{created['id']}/test-connection", params={"workspace_id": WORKSPACE_A})

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_test_connection_is_422_when_the_service_refuses_it() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store, refuse=True))
    created = client.post("/api/v1/datasources", json=_create_body()).json()

    response = client.post(f"/api/v1/datasources/{created['id']}/test-connection", params={"workspace_id": WORKSPACE_A})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "connection_refused"


def test_test_connection_is_404_for_an_unknown_data_source() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))

    response = client.post(f"/api/v1/datasources/{uuid4()}/test-connection", params={"workspace_id": WORKSPACE_A})

    assert response.status_code == 404


def test_verify_read_only_succeeds() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))
    created = client.post("/api/v1/datasources", json=_create_body()).json()

    response = client.post(f"/api/v1/datasources/{created['id']}/verify-read-only", params={"workspace_id": WORKSPACE_A})

    assert response.status_code == 200
    assert response.json()["is_read_only"] is True


def test_schemas_lists_accessible_tables() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))
    created = client.post("/api/v1/datasources", json=_create_body()).json()

    response = client.get(f"/api/v1/datasources/{created['id']}/schemas", params={"workspace_id": WORKSPACE_A})

    assert response.status_code == 200
    assert response.json()["schemas"] == ["public"]


def test_selecting_a_table_returns_the_profiled_catalog_entry() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))
    created = client.post("/api/v1/datasources", json=_create_body()).json()

    response = client.post(
        f"/api/v1/datasources/{created['id']}/tables", params={"workspace_id": WORKSPACE_A},
        json={"schema_name": "public", "technical_name": "orders", "business_name": "Orders"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["business_name"] == "Orders"
    assert body["primary_key"] == ["id"]
    assert body["measures"] == ["total"]
    assert body["approved_by"] is None


def test_correcting_a_table_resets_its_approval() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))
    created = client.post("/api/v1/datasources", json=_create_body()).json()
    table = client.post(
        f"/api/v1/datasources/{created['id']}/tables", params={"workspace_id": WORKSPACE_A},
        json={"schema_name": "public", "technical_name": "orders", "business_name": "Orders"},
    ).json()
    client.post(
        f"/api/v1/datasources/{created['id']}/tables/{table['id']}/approve", params={"workspace_id": WORKSPACE_A},
        json={"approved_by": "alice"},
    )

    response = client.patch(
        f"/api/v1/datasources/{created['id']}/tables/{table['id']}", params={"workspace_id": WORKSPACE_A},
        json={
            "business_name": "Customer Orders", "columns": [
                {"technical_name": "id", "data_type": "uuid", "role": "primary_key"},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["business_name"] == "Customer Orders"
    assert body["approved_by"] is None


def test_a_sensitive_column_correction_with_example_values_is_rejected() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))
    created = client.post("/api/v1/datasources", json=_create_body()).json()
    table = client.post(
        f"/api/v1/datasources/{created['id']}/tables", params={"workspace_id": WORKSPACE_A},
        json={"schema_name": "public", "technical_name": "orders", "business_name": "Orders"},
    ).json()

    response = client.patch(
        f"/api/v1/datasources/{created['id']}/tables/{table['id']}", params={"workspace_id": WORKSPACE_A},
        json={
            "business_name": "Orders", "columns": [
                {
                    "technical_name": "ssn", "data_type": "text", "sensitivity": "restricted",
                    "example_values": ["123-45-6789"],
                },
            ],
        },
    )

    assert response.status_code == 422


def test_setting_a_table_inactive_hides_it_from_the_active_only_list() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))
    created = client.post("/api/v1/datasources", json=_create_body()).json()
    table = client.post(
        f"/api/v1/datasources/{created['id']}/tables", params={"workspace_id": WORKSPACE_A},
        json={"schema_name": "public", "technical_name": "orders", "business_name": "Orders"},
    ).json()

    client.post(
        f"/api/v1/datasources/{created['id']}/tables/{table['id']}/active", params={"workspace_id": WORKSPACE_A},
        json={"active": False},
    )
    listed = client.get(
        f"/api/v1/datasources/{created['id']}/tables", params={"workspace_id": WORKSPACE_A, "active_only": True},
    ).json()

    assert listed["items"] == []


def test_relationship_discovery_then_approval_round_trips() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))
    created = client.post("/api/v1/datasources", json=_create_body()).json()
    client.post(
        f"/api/v1/datasources/{created['id']}/tables", params={"workspace_id": WORKSPACE_A},
        json={"schema_name": "public", "technical_name": "orders", "business_name": "Orders"},
    )

    discovered = client.post(f"/api/v1/datasources/{created['id']}/relationships/discover", params={"workspace_id": WORKSPACE_A}).json()
    assert len(discovered["items"]) == 1
    relationship_id = discovered["items"][0]["id"]

    pending = client.get(
        f"/api/v1/datasources/{created['id']}/relationships", params={"workspace_id": WORKSPACE_A, "approval_status": "pending"},
    ).json()
    assert len(pending["items"]) == 1

    approved = client.post(
        f"/api/v1/datasources/{created['id']}/relationships/{relationship_id}/approval", params={"workspace_id": WORKSPACE_A},
        json={"approval_status": "approved", "approved_by": "alice"},
    )
    assert approved.status_code == 200
    assert approved.json()["approval_status"] == "approved"

    pending_after = client.get(
        f"/api/v1/datasources/{created['id']}/relationships", params={"workspace_id": WORKSPACE_A, "approval_status": "pending"},
    ).json()
    assert pending_after["items"] == []


def test_relationship_approval_for_an_unknown_relationship_is_404() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))
    created = client.post("/api/v1/datasources", json=_create_body()).json()

    response = client.post(
        f"/api/v1/datasources/{created['id']}/relationships/{uuid4()}/approval", params={"workspace_id": WORKSPACE_A},
        json={"approval_status": "approved", "approved_by": "alice"},
    )

    assert response.status_code == 404


def test_activation_before_read_only_verification_is_refused() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))
    created = client.post("/api/v1/datasources", json=_create_body()).json()

    response = client.post(f"/api/v1/datasources/{created['id']}/activate", params={"workspace_id": WORKSPACE_A})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "activation_refused"


def test_activation_without_an_approved_table_is_refused() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))
    created = client.post("/api/v1/datasources", json=_create_body()).json()
    client.post(f"/api/v1/datasources/{created['id']}/verify-read-only", params={"workspace_id": WORKSPACE_A})
    client.post(
        f"/api/v1/datasources/{created['id']}/tables", params={"workspace_id": WORKSPACE_A},
        json={"schema_name": "public", "technical_name": "orders", "business_name": "Orders"},
    )

    response = client.post(f"/api/v1/datasources/{created['id']}/activate", params={"workspace_id": WORKSPACE_A})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "activation_refused"


def test_activation_succeeds_once_verified_and_a_table_is_approved() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))
    created = client.post("/api/v1/datasources", json=_create_body()).json()
    client.post(f"/api/v1/datasources/{created['id']}/verify-read-only", params={"workspace_id": WORKSPACE_A})
    table = client.post(
        f"/api/v1/datasources/{created['id']}/tables", params={"workspace_id": WORKSPACE_A},
        json={"schema_name": "public", "technical_name": "orders", "business_name": "Orders"},
    ).json()
    client.post(
        f"/api/v1/datasources/{created['id']}/tables/{table['id']}/approve", params={"workspace_id": WORKSPACE_A},
        json={"approved_by": "alice"},
    )

    response = client.post(f"/api/v1/datasources/{created['id']}/activate", params={"workspace_id": WORKSPACE_A})

    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_freshness_reports_health_and_latest_timestamp() -> None:
    store = FakeDataSourceStore()
    client = _client(store, FakeOnboardingService(store=store))
    created = client.post("/api/v1/datasources", json=_create_body()).json()
    client.post(
        f"/api/v1/datasources/{created['id']}/tables", params={"workspace_id": WORKSPACE_A},
        json={"schema_name": "public", "technical_name": "orders", "business_name": "Orders"},
    )

    response = client.get(f"/api/v1/datasources/{created['id']}/freshness", params={"workspace_id": WORKSPACE_A})

    assert response.status_code == 200
    body = response.json()
    assert body["stale"] is False
    assert body["latest_source_timestamp"] is not None
