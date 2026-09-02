"""Connectivity and read-only verification, against real PostgreSQL roles.

Two real roles are exercised: the admin role TEST_DATABASE_URL already
connects as (a stand-in for a workspace that misconfigured its data source
with a writable/superuser role -- exactly what onboarding must reject), and a
throwaway, genuinely restricted role created and dropped by this file's own
fixture (a stand-in for a correctly configured read-only workspace source).
Nothing here is mocked: verify_read_only's live probe is proven against a
server that actually enforces (or, for the admin role, actually permits)
writes.

Skips when TEST_DATABASE_URL is unset, like the other database tests.
"""

from __future__ import annotations

import os
import uuid

import pytest
from pytest_asyncio import fixture
from sqlalchemy import text
from sqlalchemy.engine import make_url

pytest.importorskip("sqlalchemy")

from app.analytics.connection import AnalyticsDatabase
from app.analytics.schema.allowlist import AnalyticsSchemaPolicy
from app.analytics.schema.inspector import PostgreSQLInspector
from app.analytics.sql.executor import AnalyticsSQLExecutor
from app.analytics.sql.limits import AnalyticsQueryLimits
from app.analytics.sql.validator import PostgreSQLQueryValidator
from app.datasources.connectivity import test_connection as check_connection
from app.datasources.connectivity import verify_read_only
from app.datasources.runtime import DataSourceRuntime
from app.db.session import Database

pytestmark = pytest.mark.postgres

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def _plain_runtime(dsn: str) -> DataSourceRuntime:
    """A runtime built without SSL or SSRF checks -- this file tests connectivity
    logic specifically, not the security guards already covered in
    tests/unit/datasources/test_security.py.
    """

    database = AnalyticsDatabase(dsn)
    policy = AnalyticsSchemaPolicy.for_schemas(["public"])
    return DataSourceRuntime(
        database=database, inspector=PostgreSQLInspector(database, policy),
        validator=PostgreSQLQueryValidator(policy), executor=AnalyticsSQLExecutor(database, AnalyticsQueryLimits()),
    )


@fixture
async def admin_dsn():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    yield TEST_DATABASE_URL


@fixture
async def restricted_role(admin_dsn):
    """Create a genuinely unprivileged, SELECT-only role; drop it afterward."""

    url = make_url(admin_dsn)
    role_name = f"datasource_test_ro_{uuid.uuid4().hex[:12]}"
    password = "test-readonly-password"
    admin = Database(admin_dsn)
    try:
        async with admin.session() as session:
            async with session.begin():
                # CREATE ROLE ... PASSWORD does not accept a bind parameter --
                # PostgreSQL DDL has no placeholder there. Dollar-quoting is
                # safe here specifically because this password is a fixed
                # literal this file controls, never external input.
                await session.execute(text(
                    f'CREATE ROLE "{role_name}" LOGIN PASSWORD $${password}$$ '
                    "NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS"
                ))
                await session.execute(text(f'GRANT CONNECT ON DATABASE "{url.database}" TO "{role_name}"'))
                await session.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role_name}"'))
                await session.execute(text(f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{role_name}"'))
        role_dsn = str(url.set(username=role_name, password=password))
        yield role_dsn
    finally:
        async with admin.session() as session:
            async with session.begin():
                await session.execute(text(f'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM "{role_name}"'))
                await session.execute(text(f'REVOKE ALL ON SCHEMA public FROM "{role_name}"'))
                await session.execute(text(f'REVOKE CONNECT ON DATABASE "{url.database}" FROM "{role_name}"'))
                await session.execute(text(f'DROP ROLE "{role_name}"'))
        await admin.dispose()


@pytest.mark.asyncio
async def test_connectivity_succeeds_against_a_reachable_database(admin_dsn) -> None:
    runtime = _plain_runtime(admin_dsn)
    try:
        result = await check_connection(runtime)
        assert result.success is True
        assert result.server_version is not None and "PostgreSQL" in result.server_version
    finally:
        await runtime.database.dispose()


@pytest.mark.asyncio
async def test_connectivity_fails_gracefully_against_an_unreachable_database(admin_dsn) -> None:
    url = make_url(admin_dsn).set(database="this_database_does_not_exist_at_all")
    runtime = _plain_runtime(str(url))
    try:
        result = await check_connection(runtime)
        assert result.success is False
        assert "credential" not in result.message.lower()  # never leaks driver detail
    finally:
        await runtime.database.dispose()


@pytest.mark.asyncio
async def test_a_valid_read_only_role_passes_verification(restricted_role) -> None:
    runtime = _plain_runtime(restricted_role)
    try:
        verification = await verify_read_only(runtime)
        assert verification.is_read_only is True
        assert verification.role_is_superuser is False
    finally:
        await runtime.database.dispose()


@pytest.mark.asyncio
async def test_a_writable_admin_role_is_rejected(admin_dsn) -> None:
    """The role TEST_DATABASE_URL connects as is a full read-write (often superuser) role."""

    runtime = _plain_runtime(admin_dsn)
    try:
        verification = await verify_read_only(runtime)
        assert verification.is_read_only is False
        assert "elevated privileges" in verification.message
    finally:
        await runtime.database.dispose()


@pytest.mark.asyncio
async def test_a_read_only_role_actually_cannot_write(restricted_role) -> None:
    """Independent proof, not just trusting the privilege check: attempt a real write."""

    runtime = _plain_runtime(restricted_role)
    try:
        with pytest.raises(Exception, match="(?i)read.only"):
            async with runtime.database.connection() as connection:
                async with connection.begin():
                    await connection.execute(text("SET TRANSACTION READ ONLY"))
                    await connection.execute(text("CREATE TEMP TABLE should_never_exist (x int)"))
    finally:
        await runtime.database.dispose()
