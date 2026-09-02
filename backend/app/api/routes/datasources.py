"""Workspace data source onboarding: connect, verify, select, profile, approve, activate.

Every route is workspace-scoped the same way saved reports and schedules
already are, and no response schema anywhere in this router has a field for
a password -- ``DataSourceStore.get_connection`` cannot return one even if a
caller wanted it to.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas.datasources import (
    DEFAULT_WORKSPACE_ID,
    ApproveTableRequest,
    ColumnCorrectionPayload,
    ColumnResponse,
    ConnectionTestResponse,
    DataSourceCreateRequest,
    DataSourceListResponse,
    DataSourceResponse,
    FreshnessResponse,
    ReadOnlyVerificationResponse,
    RelationshipApprovalRequest,
    RelationshipListResponse,
    RelationshipResponse,
    SchemaSummaryResponse,
    SelectTableRequest,
    TableActiveRequest,
    TableCorrectionRequest,
    TableListResponse,
    TableResponse,
)
from app.composition import get_data_source_onboarding_service, get_data_source_store
from app.datasources.contracts import (
    DataSourceConnection,
    DataSourceConnectionConfig,
    DataSourceRelationship,
    DataSourceTableCatalogEntry,
)
from app.datasources.service import (
    DataSourceConnectionRefusedError,
    DataSourceOnboardingError,
    DataSourceOnboardingService,
)
from app.datasources.store import (
    ColumnInput,
    DataSourceNotFoundError,
    DataSourceRelationshipNotFoundError,
    DataSourceStore,
    DataSourceTableNotFoundError,
)

router = APIRouter(prefix="/api/v1/datasources", tags=["datasources"])


def _not_found(data_source_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=404, detail={"code": "unknown_data_source", "message": f"Data source {data_source_id} not found."},
    )


def _onboarding_error(error: DataSourceOnboardingError, data_source_id: UUID) -> HTTPException:
    """Tell "does not exist" (404) apart from "refused for safety" (422)."""

    if isinstance(error, DataSourceConnectionRefusedError):
        return HTTPException(status_code=422, detail={"code": "connection_refused", "message": str(error)})
    return _not_found(data_source_id)


def _connection_response(connection: DataSourceConnection) -> DataSourceResponse:
    return DataSourceResponse(
        id=str(connection.id), workspace_id=connection.workspace_id, name=connection.name,
        host=connection.config.host, port=connection.config.port, database=connection.config.database,
        username=connection.config.username, ssl_mode=connection.config.ssl_mode,
        allowed_schemas=connection.config.allowed_schemas,
        statement_timeout_seconds=connection.config.statement_timeout_seconds,
        max_result_rows=connection.config.max_result_rows, max_result_bytes=connection.config.max_result_bytes,
        status=connection.status, health_status=connection.health_status,
        last_connection_at=connection.last_connection_at, last_connection_error=connection.last_connection_error,
        last_profiled_at=connection.last_profiled_at, created_at=connection.created_at, updated_at=connection.updated_at,
    )


def _table_response(table: DataSourceTableCatalogEntry) -> TableResponse:
    return TableResponse(
        id=str(table.id), data_source_id=str(table.data_source_id), schema_name=table.schema_name,
        technical_name=table.technical_name, business_name=table.business_name, description=table.description,
        grain=table.grain, freshness_column=table.freshness_column, active=table.active,
        approved_by=table.approved_by, approved_at=table.approved_at,
        columns=[
            ColumnResponse(
                id=str(column.id), technical_name=column.technical_name, data_type=column.data_type,
                role=column.role, sensitivity=column.sensitivity, excluded=column.excluded,
                example_values=column.example_values,
            )
            for column in table.columns
        ],
        primary_key=table.primary_key, dimensions=table.dimensions, measures=table.measures,
        time_columns=table.time_columns, sensitive_columns=table.sensitive_columns,
        created_at=table.created_at, updated_at=table.updated_at,
    )


def _relationship_response(relationship: DataSourceRelationship) -> RelationshipResponse:
    return RelationshipResponse(
        id=str(relationship.id), data_source_id=str(relationship.data_source_id),
        source_table=relationship.source_table, source_column=relationship.source_column,
        target_table=relationship.target_table, target_column=relationship.target_column,
        cardinality=relationship.cardinality, confidence=relationship.confidence,
        discovery_method=relationship.discovery_method, approval_status=relationship.approval_status,
        approved_by=relationship.approved_by, approved_at=relationship.approved_at,
        created_at=relationship.created_at, updated_at=relationship.updated_at,
    )


def _columns(payloads: list[ColumnCorrectionPayload]) -> list[ColumnInput]:
    return [
        ColumnInput(
            technical_name=item.technical_name, data_type=item.data_type, role=item.role,
            sensitivity=item.sensitivity, excluded=item.excluded, example_values=item.example_values,
        )
        for item in payloads
    ]


# -- connections ------------------------------------------------------------


@router.post("", response_model=DataSourceResponse, status_code=201)
async def create_data_source(
    request: DataSourceCreateRequest, service: DataSourceOnboardingService = Depends(get_data_source_onboarding_service),
) -> DataSourceResponse:
    config = DataSourceConnectionConfig(
        host=request.host, port=request.port, database=request.database, username=request.username,
        ssl_mode=request.ssl_mode, allowed_schemas=request.allowed_schemas,
        statement_timeout_seconds=request.statement_timeout_seconds, max_result_rows=request.max_result_rows,
        max_result_bytes=request.max_result_bytes,
    )
    connection = await service.create_connection(
        workspace_id=request.workspace_id, name=request.name, config=config, password=request.password,
    )
    return _connection_response(connection)


@router.get("", response_model=DataSourceListResponse)
async def list_data_sources(
    workspace_id: str = Query(default=DEFAULT_WORKSPACE_ID),
    status: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    store: DataSourceStore = Depends(get_data_source_store),
) -> DataSourceListResponse:
    items, total = await store.list_connections(workspace_id=workspace_id, status=status, limit=limit, offset=offset)
    return DataSourceListResponse(items=[_connection_response(item) for item in items], total=total, limit=limit, offset=offset)


@router.get("/{data_source_id}", response_model=DataSourceResponse)
async def get_data_source(
    data_source_id: UUID, workspace_id: str = Query(default=DEFAULT_WORKSPACE_ID),
    store: DataSourceStore = Depends(get_data_source_store),
) -> DataSourceResponse:
    connection = await store.get_connection(workspace_id=workspace_id, data_source_id=data_source_id)
    if connection is None:
        raise _not_found(data_source_id)
    return _connection_response(connection)


@router.post("/{data_source_id}/test-connection", response_model=ConnectionTestResponse)
async def test_data_source_connection(
    data_source_id: UUID, workspace_id: str = Query(default=DEFAULT_WORKSPACE_ID),
    service: DataSourceOnboardingService = Depends(get_data_source_onboarding_service),
) -> ConnectionTestResponse:
    try:
        result = await service.test_connectivity(workspace_id=workspace_id, data_source_id=data_source_id)
    except DataSourceOnboardingError as error:
        raise _onboarding_error(error, data_source_id) from error
    return ConnectionTestResponse(success=result.success, message=result.message, server_version=result.server_version)


@router.post("/{data_source_id}/verify-read-only", response_model=ReadOnlyVerificationResponse)
async def verify_data_source_read_only(
    data_source_id: UUID, workspace_id: str = Query(default=DEFAULT_WORKSPACE_ID),
    service: DataSourceOnboardingService = Depends(get_data_source_onboarding_service),
) -> ReadOnlyVerificationResponse:
    try:
        verification = await service.verify_read_only_behavior(workspace_id=workspace_id, data_source_id=data_source_id)
    except DataSourceOnboardingError as error:
        raise _onboarding_error(error, data_source_id) from error
    return ReadOnlyVerificationResponse(
        is_read_only=verification.is_read_only, role_is_superuser=verification.role_is_superuser,
        role_can_create_database=verification.role_can_create_database,
        role_can_create_role=verification.role_can_create_role,
        role_bypasses_row_level_security=verification.role_bypasses_row_level_security,
        message=verification.message,
    )


@router.get("/{data_source_id}/schemas", response_model=SchemaSummaryResponse)
async def list_data_source_schemas(
    data_source_id: UUID, workspace_id: str = Query(default=DEFAULT_WORKSPACE_ID),
    service: DataSourceOnboardingService = Depends(get_data_source_onboarding_service),
) -> SchemaSummaryResponse:
    try:
        summary = await service.list_accessible_schemas(workspace_id=workspace_id, data_source_id=data_source_id)
    except DataSourceOnboardingError as error:
        raise _onboarding_error(error, data_source_id) from error
    return SchemaSummaryResponse(
        schemas=summary.schemas, tables=[table.model_dump(by_alias=True) for table in summary.tables],
    )


@router.post("/{data_source_id}/activate", response_model=DataSourceResponse)
async def activate_data_source(
    data_source_id: UUID, workspace_id: str = Query(default=DEFAULT_WORKSPACE_ID),
    service: DataSourceOnboardingService = Depends(get_data_source_onboarding_service),
) -> DataSourceResponse:
    try:
        connection = await service.activate(workspace_id=workspace_id, data_source_id=data_source_id)
    except DataSourceOnboardingError as error:
        if "not found" in str(error).lower():
            raise _not_found(data_source_id) from error
        raise HTTPException(status_code=422, detail={"code": "activation_refused", "message": str(error)}) from error
    return _connection_response(connection)


@router.get("/{data_source_id}/freshness", response_model=FreshnessResponse)
async def get_data_source_freshness(
    data_source_id: UUID, workspace_id: str = Query(default=DEFAULT_WORKSPACE_ID),
    service: DataSourceOnboardingService = Depends(get_data_source_onboarding_service),
) -> FreshnessResponse:
    try:
        snapshot = await service.check_freshness(workspace_id=workspace_id, data_source_id=data_source_id)
    except DataSourceOnboardingError as error:
        raise _onboarding_error(error, data_source_id) from error
    return FreshnessResponse(
        data_source_id=str(snapshot.data_source_id), checked_at=snapshot.checked_at,
        latest_source_timestamp=snapshot.latest_source_timestamp, stale=snapshot.stale,
        health_status=snapshot.health_status, per_table=snapshot.per_table,
    )


# -- catalog: tables ----------------------------------------------------------


@router.post("/{data_source_id}/tables", response_model=TableResponse, status_code=201)
async def select_data_source_table(
    data_source_id: UUID, request: SelectTableRequest, workspace_id: str = Query(default=DEFAULT_WORKSPACE_ID),
    service: DataSourceOnboardingService = Depends(get_data_source_onboarding_service),
) -> TableResponse:
    try:
        table = await service.select_and_profile_table(
            workspace_id=workspace_id, data_source_id=data_source_id, schema_name=request.schema_name,
            technical_name=request.technical_name, business_name=request.business_name,
            description=request.description, grain=request.grain, freshness_column=request.freshness_column,
        )
    except DataSourceOnboardingError as error:
        raise _onboarding_error(error, data_source_id) from error
    return _table_response(table)


@router.get("/{data_source_id}/tables", response_model=TableListResponse)
async def list_data_source_tables(
    data_source_id: UUID, workspace_id: str = Query(default=DEFAULT_WORKSPACE_ID),
    active_only: bool = Query(default=False),
    store: DataSourceStore = Depends(get_data_source_store),
) -> TableListResponse:
    tables = await store.list_tables(workspace_id=workspace_id, data_source_id=data_source_id, active_only=active_only)
    if tables is None:
        raise _not_found(data_source_id)
    return TableListResponse(items=[_table_response(table) for table in tables])


@router.get("/{data_source_id}/tables/{table_id}", response_model=TableResponse)
async def get_data_source_table(
    data_source_id: UUID, table_id: UUID, workspace_id: str = Query(default=DEFAULT_WORKSPACE_ID),
    store: DataSourceStore = Depends(get_data_source_store),
) -> TableResponse:
    table = await store.get_table(workspace_id=workspace_id, data_source_id=data_source_id, table_id=table_id)
    if table is None:
        raise HTTPException(status_code=404, detail={"code": "unknown_table", "message": f"Table {table_id} not found."})
    return _table_response(table)


@router.patch("/{data_source_id}/tables/{table_id}", response_model=TableResponse)
async def correct_data_source_table(
    data_source_id: UUID, table_id: UUID, request: TableCorrectionRequest,
    workspace_id: str = Query(default=DEFAULT_WORKSPACE_ID), store: DataSourceStore = Depends(get_data_source_store),
) -> TableResponse:
    existing = await store.get_table(workspace_id=workspace_id, data_source_id=data_source_id, table_id=table_id)
    if existing is None:
        raise HTTPException(status_code=404, detail={"code": "unknown_table", "message": f"Table {table_id} not found."})
    try:
        table = await store.upsert_table(
            workspace_id=workspace_id, data_source_id=data_source_id, schema_name=existing.schema_name,
            technical_name=existing.technical_name, business_name=request.business_name,
            description=request.description, grain=request.grain, freshness_column=request.freshness_column,
            columns=_columns(request.columns),
        )
    except DataSourceNotFoundError as error:
        raise _not_found(data_source_id) from error
    return _table_response(table)


@router.post("/{data_source_id}/tables/{table_id}/active", response_model=TableResponse)
async def set_data_source_table_active(
    data_source_id: UUID, table_id: UUID, request: TableActiveRequest,
    workspace_id: str = Query(default=DEFAULT_WORKSPACE_ID), store: DataSourceStore = Depends(get_data_source_store),
) -> TableResponse:
    try:
        table = await store.set_table_active(
            workspace_id=workspace_id, data_source_id=data_source_id, table_id=table_id, active=request.active,
        )
    except DataSourceNotFoundError as error:
        raise _not_found(data_source_id) from error
    except DataSourceTableNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "unknown_table", "message": str(error)}) from error
    return _table_response(table)


@router.post("/{data_source_id}/tables/{table_id}/approve", response_model=TableResponse)
async def approve_data_source_table(
    data_source_id: UUID, table_id: UUID, request: ApproveTableRequest,
    workspace_id: str = Query(default=DEFAULT_WORKSPACE_ID), store: DataSourceStore = Depends(get_data_source_store),
) -> TableResponse:
    try:
        table = await store.approve_table(
            workspace_id=workspace_id, data_source_id=data_source_id, table_id=table_id,
            approved_by=request.approved_by,
        )
    except DataSourceNotFoundError as error:
        raise _not_found(data_source_id) from error
    except DataSourceTableNotFoundError as error:
        raise HTTPException(status_code=404, detail={"code": "unknown_table", "message": str(error)}) from error
    return _table_response(table)


# -- catalog: relationships ----------------------------------------------------


@router.post("/{data_source_id}/relationships/discover", response_model=RelationshipListResponse)
async def discover_data_source_relationships(
    data_source_id: UUID, workspace_id: str = Query(default=DEFAULT_WORKSPACE_ID),
    service: DataSourceOnboardingService = Depends(get_data_source_onboarding_service),
) -> RelationshipListResponse:
    try:
        relationships = await service.discover_table_relationships(workspace_id=workspace_id, data_source_id=data_source_id)
    except DataSourceOnboardingError as error:
        raise _onboarding_error(error, data_source_id) from error
    return RelationshipListResponse(items=[_relationship_response(item) for item in relationships])


@router.get("/{data_source_id}/relationships", response_model=RelationshipListResponse)
async def list_data_source_relationships(
    data_source_id: UUID, workspace_id: str = Query(default=DEFAULT_WORKSPACE_ID),
    approval_status: str | None = Query(default=None),
    store: DataSourceStore = Depends(get_data_source_store),
) -> RelationshipListResponse:
    relationships = await store.list_relationships(
        workspace_id=workspace_id, data_source_id=data_source_id, approval_status=approval_status,
    )
    if relationships is None:
        raise _not_found(data_source_id)
    return RelationshipListResponse(items=[_relationship_response(item) for item in relationships])


@router.post("/{data_source_id}/relationships/{relationship_id}/approval", response_model=RelationshipResponse)
async def set_data_source_relationship_approval(
    data_source_id: UUID, relationship_id: UUID, request: RelationshipApprovalRequest,
    workspace_id: str = Query(default=DEFAULT_WORKSPACE_ID), store: DataSourceStore = Depends(get_data_source_store),
) -> RelationshipResponse:
    try:
        relationship = await store.set_relationship_approval(
            workspace_id=workspace_id, data_source_id=data_source_id, relationship_id=relationship_id,
            approval_status=request.approval_status, approved_by=request.approved_by,
        )
    except DataSourceNotFoundError as error:
        raise _not_found(data_source_id) from error
    except DataSourceRelationshipNotFoundError as error:
        raise HTTPException(
            status_code=404, detail={"code": "unknown_relationship", "message": str(error)},
        ) from error
    return _relationship_response(relationship)
