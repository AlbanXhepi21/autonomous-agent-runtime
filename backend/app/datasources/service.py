"""Orchestrates the onboarding flow's steps that need a live, decrypted connection.

Nothing here is a new algorithm -- every step delegates to a module that
already owns its own logic and its own tests (security, encryption,
connectivity, profiling, runtime). This class exists to sequence them the
same way every time, and to be the only place a decrypted password exists
outside ``app.datasources.encryption`` -- ``_runtime_for`` decrypts it,
builds a runtime, and the plaintext never survives past that call's stack.

Steps that are plain CRUD against the catalog (approving a table, correcting
its metadata, approving or rejecting a relationship) do not need a live
connection and go straight through ``DataSourceStore`` from the API layer
instead of being wrapped here a second time.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.analytics.schema.contracts import DatabaseSchemaSummary
from app.datasources.connectivity import test_connection, verify_read_only
from app.datasources.contracts import (
    ConnectionTestResult,
    DataSourceConnection,
    DataSourceConnectionConfig,
    DataSourceRelationship,
    DataSourceTableCatalogEntry,
    FreshnessSnapshot,
    ReadOnlyVerification,
)
from app.datasources.encryption import SecretCipher, SecretCipherError
from app.datasources.freshness import compute_freshness
from app.datasources.profiling import discover_relationships, profile_table, suggest_role, suggest_sensitivity
from app.datasources.runtime import DataSourceRuntime, build_data_source_runtime
from app.datasources.security import ConnectionSecurityError
from app.datasources.store import ColumnInput, DataSourceStore


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DataSourceOnboardingError(Exception):
    """Raised when an onboarding step cannot proceed as asked."""


class DataSourceConnectionRefusedError(DataSourceOnboardingError):
    """Raised when a security guard (SSRF, SSL mode, credential) refuses a connection.

    Distinct from the base class so an API route can tell "this data source
    does not exist" (404) apart from "it exists, but is not safe to connect
    to" (422) -- both currently reach a caller through the same
    ``_runtime_for`` call, but they are not the same kind of failure.
    """


class DataSourceOnboardingService:
    def __init__(
        self, *, store: DataSourceStore, cipher: SecretCipher, allow_local_hosts: bool = False,
        schema_cache_ttl_seconds: float = 300, freshness_stale_after: timedelta = timedelta(hours=48),
    ) -> None:
        self._store = store
        self._cipher = cipher
        self._allow_local_hosts = allow_local_hosts
        self._schema_cache_ttl_seconds = schema_cache_ttl_seconds
        self._freshness_stale_after = freshness_stale_after

    async def _runtime_for(self, *, workspace_id: str, data_source_id: UUID) -> tuple[DataSourceConnection, DataSourceRuntime]:
        connection = await self._store.get_connection(workspace_id=workspace_id, data_source_id=data_source_id)
        if connection is None:
            raise DataSourceOnboardingError("Data source not found.")
        encrypted = await self._store.get_encrypted_password(workspace_id=workspace_id, data_source_id=data_source_id)
        assert encrypted is not None, "a connection that exists always has an encrypted password"
        try:
            password = self._cipher.decrypt(encrypted)
            runtime = build_data_source_runtime(
                connection, password=password, allow_local_hosts=self._allow_local_hosts,
                schema_cache_ttl_seconds=self._schema_cache_ttl_seconds,
            )
        except (ConnectionSecurityError, SecretCipherError) as error:
            # A security-guard refusal is a real, safe-to-persist outcome for
            # this connection, not just a transient API error -- recorded the
            # same way a failed connectivity test or read-only check is.
            await self._store.update_connection_status(
                workspace_id=workspace_id, data_source_id=data_source_id, status="failed",
                health_status="unreachable", last_connection_at=_now(), last_connection_error=str(error),
            )
            raise DataSourceConnectionRefusedError(str(error)) from error
        return connection, runtime

    # -- step 1: create -----------------------------------------------------

    async def create_connection(
        self, *, workspace_id: str, name: str, config: DataSourceConnectionConfig, password: str,
    ) -> DataSourceConnection:
        encrypted = self._cipher.encrypt(password)
        return await self._store.create_connection(
            workspace_id=workspace_id, name=name, config=config, encrypted_password=encrypted,
        )

    # -- step 2: test connectivity -------------------------------------------

    async def test_connectivity(self, *, workspace_id: str, data_source_id: UUID) -> ConnectionTestResult:
        _connection, runtime = await self._runtime_for(workspace_id=workspace_id, data_source_id=data_source_id)
        try:
            result = await test_connection(runtime)
            await self._store.update_connection_status(
                workspace_id=workspace_id, data_source_id=data_source_id,
                status="testing" if result.success else "failed",
                last_connection_at=_now(), last_connection_error=None if result.success else result.message,
            )
        finally:
            await runtime.database.dispose()
        return result

    # -- step 3: verify read-only behavior -----------------------------------

    async def verify_read_only_behavior(self, *, workspace_id: str, data_source_id: UUID) -> ReadOnlyVerification:
        _connection, runtime = await self._runtime_for(workspace_id=workspace_id, data_source_id=data_source_id)
        try:
            verification = await verify_read_only(runtime)
            await self._store.update_connection_status(
                workspace_id=workspace_id, data_source_id=data_source_id,
                status="verified_read_only" if verification.is_read_only else "failed",
                health_status="healthy" if verification.is_read_only else "unreachable",
                last_connection_at=_now(),
                last_connection_error=None if verification.is_read_only else verification.message,
            )
        finally:
            await runtime.database.dispose()
        return verification

    # -- step 4: list accessible schemas -------------------------------------

    async def list_accessible_schemas(self, *, workspace_id: str, data_source_id: UUID) -> DatabaseSchemaSummary:
        _connection, runtime = await self._runtime_for(workspace_id=workspace_id, data_source_id=data_source_id)
        try:
            return await runtime.inspector.list_tables()
        finally:
            await runtime.database.dispose()

    # -- steps 5-6: select a table and profile it in the same call ----------

    async def select_and_profile_table(
        self, *, workspace_id: str, data_source_id: UUID, schema_name: str, technical_name: str,
        business_name: str, description: str | None = None, grain: str | None = None,
        freshness_column: str | None = None,
    ) -> DataSourceTableCatalogEntry:
        """Profile the table live, suggest a classification for each column, and store it.

        The suggestion is exactly that -- step 8 ("let an authorized user
        approve or correct metadata") is what turns a suggestion into
        something the agent may rely on; nothing here marks a table approved.
        """

        _connection, runtime = await self._runtime_for(workspace_id=workspace_id, data_source_id=data_source_id)
        try:
            profile = await profile_table(runtime, schema_name=schema_name, technical_name=technical_name)
        finally:
            await runtime.database.dispose()

        columns = []
        for column in profile.columns:
            sensitivity = suggest_sensitivity(column.name)
            columns.append(ColumnInput(
                technical_name=column.name, data_type=column.data_type,
                role=suggest_role(
                    name=column.name, data_type=column.data_type, primary_key=column.primary_key,
                    foreign_key_target=column.foreign_key_target,
                ),
                sensitivity=sensitivity,
                # A suggested default only -- an authentication secret is
                # suggested excluded so the common case needs no correction,
                # not because this module trusts its own name-based guess.
                excluded=sensitivity == "authentication_secret",
            ))

        table = await self._store.upsert_table(
            workspace_id=workspace_id, data_source_id=data_source_id, schema_name=schema_name,
            technical_name=technical_name, business_name=business_name, description=description,
            grain=grain, freshness_column=freshness_column, columns=columns,
        )
        await self._store.update_connection_status(
            workspace_id=workspace_id, data_source_id=data_source_id, last_profiled_at=_now(),
        )
        return table

    # -- step 7: discover candidate relationships ----------------------------

    async def discover_table_relationships(
        self, *, workspace_id: str, data_source_id: UUID,
    ) -> list[DataSourceRelationship]:
        tables = await self._store.list_tables(workspace_id=workspace_id, data_source_id=data_source_id, active_only=True)
        if tables is None:
            raise DataSourceOnboardingError("Data source not found.")
        _connection, runtime = await self._runtime_for(workspace_id=workspace_id, data_source_id=data_source_id)
        try:
            candidates = await discover_relationships(runtime, table_names=[table.technical_name for table in tables])
        finally:
            await runtime.database.dispose()
        return await self._store.create_relationship_candidates(
            workspace_id=workspace_id, data_source_id=data_source_id, candidates=candidates,
        )

    # -- step 9: activate -----------------------------------------------------

    async def activate(self, *, workspace_id: str, data_source_id: UUID) -> DataSourceConnection:
        connection = await self._store.get_connection(workspace_id=workspace_id, data_source_id=data_source_id)
        if connection is None:
            raise DataSourceOnboardingError("Data source not found.")
        if connection.status != "verified_read_only":
            raise DataSourceOnboardingError(
                "A data source must pass read-only verification before it can be activated."
            )
        tables = await self._store.list_tables(workspace_id=workspace_id, data_source_id=data_source_id, active_only=True)
        if not tables or not any(table.approved_by for table in tables):
            raise DataSourceOnboardingError(
                "At least one table must be reviewed and approved before activation."
            )
        return await self._store.update_connection_status(
            workspace_id=workspace_id, data_source_id=data_source_id, status="active",
        )

    # -- agent integration: the one connection a run should use -------------

    async def active_connection_runtime(self, *, workspace_id: str) -> tuple[DataSourceConnection, DataSourceRuntime]:
        """The connection an agent run against this workspace should use.

        Raises DataSourceOnboardingError when the workspace has no active
        connection -- a caller that explicitly asked for a workspace must
        never silently fall back to the demo database.
        """

        items, _total = await self._store.list_connections(workspace_id=workspace_id, status="active", limit=1, offset=0)
        if not items:
            raise DataSourceOnboardingError(f"Workspace {workspace_id!r} has no active data source.")
        return await self._runtime_for(workspace_id=workspace_id, data_source_id=items[0].id)

    # -- freshness --------------------------------------------------------

    async def check_freshness(self, *, workspace_id: str, data_source_id: UUID) -> FreshnessSnapshot:
        tables = await self._store.list_tables(workspace_id=workspace_id, data_source_id=data_source_id, active_only=True)
        if tables is None:
            raise DataSourceOnboardingError("Data source not found.")
        connection, runtime = await self._runtime_for(workspace_id=workspace_id, data_source_id=data_source_id)
        try:
            snapshot = await compute_freshness(
                runtime, data_source_id=data_source_id, tables=tables,
                stale_after=self._freshness_stale_after, health_status=connection.health_status,
            )
        finally:
            await runtime.database.dispose()
        await self._store.update_connection_status(
            workspace_id=workspace_id, data_source_id=data_source_id, last_profiled_at=_now(),
        )
        return snapshot
