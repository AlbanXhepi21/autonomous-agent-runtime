"""Onboarding steps 2-3: prove a connection works, and that it truly cannot write.

Two different questions, checked two different ways. "Does this connection
reach a database at all" is answered by opening one and running the
cheapest possible query. "Can this role write" is answered twice, on
purpose: once from the role's own catalog privileges (a static check that
holds even if application code ever forgets to scope a transaction), and
once by a live probe that only succeeds if PostgreSQL itself actually
refuses a write inside ``SET TRANSACTION READ ONLY`` for this specific
server and role. Both must pass before a connection can leave "testing".
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.analytics.connection import AnalyticsDatabaseError
from app.core.logging import log_event, safe_error_message
from app.datasources.contracts import ConnectionTestResult, ReadOnlyVerification
from app.datasources.runtime import DataSourceRuntime

_logger = logging.getLogger(__name__)

#: Never actually created -- PostgreSQL must refuse this inside a read-only
#: transaction before the CREATE TEMP TABLE statement does anything at all.
_PROBE_STATEMENT = "CREATE TEMP TABLE __datasource_readonly_probe (probe integer)"
_READ_ONLY_ERROR_MARKERS = ("read-only transaction", "readonlysqltransaction")


async def test_connection(runtime: DataSourceRuntime) -> ConnectionTestResult:
    """Onboarding step 2: can this connection reach its database at all?"""

    try:
        async with runtime.database.connection() as connection:
            version = (await connection.execute(text("SELECT version()"))).scalar_one()
    except AnalyticsDatabaseError as error:
        return ConnectionTestResult(success=False, message=str(error))
    except SQLAlchemyError as error:
        log_event(_logger, logging.WARNING, "datasource_connection_test_failed", error=safe_error_message(error))
        return ConnectionTestResult(success=False, message="The database rejected the connection.")
    return ConnectionTestResult(success=True, message="Connected successfully.", server_version=str(version)[:128])


async def verify_read_only(runtime: DataSourceRuntime) -> ReadOnlyVerification:
    """Onboarding step 3: confirm the role cannot write, from both directions."""

    privileges = await _role_privileges(runtime)
    if privileges is None:
        return ReadOnlyVerification(
            is_read_only=False, role_is_superuser=False, role_can_create_database=False,
            role_can_create_role=False, role_bypasses_row_level_security=False,
            message="The connected role's privileges could not be verified.",
        )
    role_is_superuser, role_can_create_database, role_can_create_role, role_bypasses_rls = privileges
    if role_is_superuser or role_can_create_database or role_can_create_role or role_bypasses_rls:
        return ReadOnlyVerification(
            is_read_only=False, role_is_superuser=role_is_superuser,
            role_can_create_database=role_can_create_database, role_can_create_role=role_can_create_role,
            role_bypasses_row_level_security=role_bypasses_rls,
            message="The connected role has elevated privileges beyond read-only and is refused.",
        )

    if not await _read_only_transaction_is_enforced(runtime):
        return ReadOnlyVerification(
            is_read_only=False, role_is_superuser=False, role_can_create_database=False,
            role_can_create_role=False, role_bypasses_row_level_security=False,
            message="This server did not enforce a read-only transaction as expected.",
        )
    return ReadOnlyVerification(
        is_read_only=True, role_is_superuser=False, role_can_create_database=False,
        role_can_create_role=False, role_bypasses_row_level_security=False,
        message="The role has no elevated privileges, and this server enforces read-only transactions.",
    )


async def _role_privileges(runtime: DataSourceRuntime) -> tuple[bool, bool, bool, bool] | None:
    try:
        async with runtime.database.connection() as connection:
            row = (await connection.execute(text(
                "SELECT rolsuper, rolcreatedb, rolcreaterole, rolbypassrls "
                "FROM pg_roles WHERE rolname = current_user"
            ))).one()
    except (AnalyticsDatabaseError, SQLAlchemyError) as error:
        log_event(_logger, logging.WARNING, "datasource_privilege_check_failed", error=safe_error_message(error))
        return None
    return bool(row[0]), bool(row[1]), bool(row[2]), bool(row[3])


async def _read_only_transaction_is_enforced(runtime: DataSourceRuntime) -> bool:
    """True only if the probe statement was itself refused as a write.

    Never committed either way: the probe either raises (rolled back
    automatically by ``connection.begin()``) or the transaction is simply
    never committed, so no temp table can ever persist from this check.
    """

    try:
        async with runtime.database.connection() as connection:
            async with connection.begin():
                await connection.execute(text("SET TRANSACTION READ ONLY"))
                await connection.execute(text(_PROBE_STATEMENT))
    except (AnalyticsDatabaseError, SQLAlchemyError) as error:
        message = safe_error_message(error).lower()
        if any(marker in message for marker in _READ_ONLY_ERROR_MARKERS):
            return True
        log_event(_logger, logging.WARNING, "datasource_readonly_probe_errored", error=safe_error_message(error))
        return False
    # The probe statement did not raise at all -- this server let a write
    # proceed inside a transaction we explicitly marked read-only.
    return False
