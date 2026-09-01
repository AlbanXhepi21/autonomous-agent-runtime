"""DA2 AST validation, limits, security, and trace coverage."""

from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.analytics.schema.allowlist import AnalyticsSchemaPolicy
from app.analytics.schema.contracts import DatabaseSchemaSummary, DatabaseTable
from app.analytics.sql.contracts import SQLColumn, SQLQueryResult
from app.analytics.sql.executor import AnalyticsQueryError, AnalyticsSQLExecutor, _serialize_value
from app.analytics.sql.limits import AnalyticsQueryLimits
from app.analytics.sql.validator import PostgreSQLQueryValidator
from app.contracts.specialists import AgentDefinition
from app.observability import InMemoryTraceStore, TraceEventType, TraceRecorder
from app.security import Capability, PolicyDecision, SecurityAction, SecurityPolicy, SecuritySubject
from app.tools.database.query import QueryDatabaseTool
from app.tools.execution import ToolExecutor
from app.tools.registry import ToolRegistry


@pytest.fixture
def validator() -> PostgreSQLQueryValidator:
    return PostgreSQLQueryValidator(AnalyticsSchemaPolicy.configured("public"))


@pytest.mark.parametrize("sql", [
    "SELECT id FROM orders",
    "SELECT o.customer_id, COUNT(*) FROM orders o JOIN customers c ON c.id = o.customer_id GROUP BY o.customer_id HAVING COUNT(*) > 1",
    "WITH recent AS (SELECT * FROM orders) SELECT COUNT(*) FROM recent",
    "SELECT * FROM (SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS rank FROM orders) ranked WHERE rank = 1",
    "SELECT CASE WHEN status = 'paid' THEN 1 ELSE 0 END FROM orders",
])
def test_validator_accepts_read_only_analytical_selects(validator: PostgreSQLQueryValidator, sql: str) -> None:
    result = validator.validate(sql, allowed_tables=["orders", "customers"])
    assert result.valid and result.statement_type == "SELECT"


@pytest.mark.parametrize("sql", [
    "INSERT INTO orders VALUES (1)", "UPDATE orders SET status = 'x'", "DELETE FROM orders",
    "DROP TABLE orders", "ALTER TABLE orders ADD x int", "TRUNCATE orders", "CREATE TABLE x (id int)",
    "COPY orders TO '/tmp/x'", "CALL dangerous()", "DO $$ BEGIN END $$", "GRANT SELECT ON orders TO x",
    "REVOKE SELECT ON orders FROM x", "SELECT * FROM orders; DELETE FROM orders",
    "WITH changed AS (DELETE FROM orders RETURNING *) SELECT * FROM changed",
    "SELECT * FROM pg_catalog.pg_tables", "SELECT * FROM information_schema.tables", "SELECT pg_sleep(2)",
    "SELECT * FROM orders FOR UPDATE", "SELECT * INTO copied_orders FROM orders",
])
def test_validator_rejects_mutating_and_adversarial_sql(validator: PostgreSQLQueryValidator, sql: str) -> None:
    result = validator.validate(sql, allowed_tables=["orders"])
    assert not result.valid


def test_validator_rejects_unknown_and_cross_schema_tables(validator: PostgreSQLQueryValidator) -> None:
    assert not validator.validate("SELECT * FROM payments", allowed_tables=["orders"]).valid
    assert not validator.validate("SELECT * FROM private.orders", allowed_tables=["orders"]).valid


class Inspector:
    async def list_tables(self) -> DatabaseSchemaSummary:
        return DatabaseSchemaSummary(schemas=["public"], tables=[DatabaseTable(name="orders", schema="public")])


class Executor:
    async def execute(self, sql: str, *, referenced_tables: list[str]) -> SQLQueryResult:
        return SQLQueryResult(columns=[SQLColumn(name="count")], rows=[["2"]], row_count=1, execution_ms=4, referenced_tables=referenced_tables)


@pytest.mark.asyncio
async def test_query_tool_and_trace_are_bounded_and_safe() -> None:
    tool = QueryDatabaseTool(Inspector(), PostgreSQLQueryValidator(AnalyticsSchemaPolicy.configured("public")), Executor())  # type: ignore[arg-type]
    registry, store = ToolRegistry(), InMemoryTraceStore()
    registry.register(tool)
    recorder = TraceRecorder(store)
    recorder.start_run(run_id="sql-run", parent_run_id=None, agent_name="data_analyst", agent_type="specialist", goal="count")
    policy = SecurityPolicy.primary().with_specialist(AgentDefinition(name="data_analyst", description="x", version="1", instructions="x", allowed_tools=["query_database"]))
    result = await ToolExecutor(registry, security_policy=policy, trace_recorder=recorder).execute("query_database", {"sql": "SELECT COUNT(*) FROM orders"}, run_id="sql-run", subject=SecuritySubject(agent_name="data_analyst", agent_type="specialist", run_id="sql-run"))

    assert result.success and result.output["rows"] == [["2"]]
    trace = store.get("sql-run")
    assert trace is not None
    events = {event.event_type for event in trace.events}
    assert {TraceEventType.DATABASE_QUERY_VALIDATION_STARTED, TraceEventType.DATABASE_QUERY_VALIDATED, TraceEventType.DATABASE_QUERY_STARTED, TraceEventType.DATABASE_QUERY_FINISHED} <= events
    assert "SELECT COUNT(*) FROM orders" not in trace.model_dump_json()


@pytest.mark.asyncio
async def test_explicit_developer_sql_trace_retains_only_successful_bounded_sql() -> None:
    tool = QueryDatabaseTool(Inspector(), PostgreSQLQueryValidator(AnalyticsSchemaPolicy.configured("public")), Executor())  # type: ignore[arg-type]
    registry, store = ToolRegistry(), InMemoryTraceStore()
    registry.register(tool)
    recorder = TraceRecorder(store)
    recorder.start_run(run_id="sql-dev", parent_run_id=None, agent_name="data_analyst", agent_type="specialist", goal="count")
    policy = SecurityPolicy.primary().with_specialist(AgentDefinition(name="data_analyst", description="x", version="1", instructions="x", allowed_tools=["query_database"]))

    result = await ToolExecutor(registry, security_policy=policy, trace_recorder=recorder, expose_sql=True, max_sql_chars=12).execute("query_database", {"sql": "SELECT COUNT(*) FROM orders"}, run_id="sql-dev", subject=SecuritySubject(agent_name="data_analyst", agent_type="specialist", run_id="sql-dev"))

    assert result.success
    trace = store.get("sql-dev")
    assert trace is not None
    completed = next(event for event in trace.events if event.event_type is TraceEventType.DATABASE_QUERY_FINISHED)
    assert completed.metadata["sql"] == "SELECT COUNT"


@pytest.mark.asyncio
async def test_query_tool_rejects_before_executor() -> None:
    tool = QueryDatabaseTool(Inspector(), PostgreSQLQueryValidator(AnalyticsSchemaPolicy.configured("public")), Executor())  # type: ignore[arg-type]
    registry = ToolRegistry(); registry.register(tool)
    result = await ToolExecutor(registry).execute("query_database", {"sql": "DELETE FROM orders"})
    assert not result.success and result.metadata["failure_category"] == "database_query_rejected"


def test_query_capability_is_separate_and_medium_resource_risk() -> None:
    policy = SecurityPolicy.primary().with_specialist(AgentDefinition(name="data_analyst", description="x", version="1", instructions="x", allowed_tools=["query_database"]))
    subject = SecuritySubject(agent_name="data_analyst", agent_type="specialist", run_id="r")
    result = policy.evaluate(subject, SecurityAction(capability=Capability.DATABASE_QUERY_READ))
    assert result.decision is PolicyDecision.ALLOW and result.metadata["risk_level"] == "medium"
    denied = policy.evaluate(SecuritySubject(agent_name="research", agent_type="specialist", run_id="r"), SecurityAction(capability=Capability.DATABASE_QUERY_READ))
    assert denied.decision is PolicyDecision.DENY


def test_result_value_serialization_preserves_analytical_values() -> None:
    assert _serialize_value(Decimal("12.340")) == "12.340"
    assert _serialize_value(date(2026, 1, 2)) == "2026-01-02"
    assert _serialize_value(datetime(2026, 1, 2, tzinfo=timezone.utc)).endswith("+00:00")
    assert _serialize_value(uuid4())
    assert _serialize_value({"total": Decimal("1.20")}) == {"total": "1.20"}


class StreamResult:
    def __init__(self, rows: list[list[object]]) -> None:
        self.rows = rows
    def keys(self) -> list[str]: return ["value"]
    async def fetchmany(self, size: int) -> list[list[object]]:
        batch, self.rows = self.rows[:size], self.rows[size:]
        return batch
    async def close(self) -> None: pass


class Connection:
    def __init__(self, rows: list[list[object]], error: Exception | None = None) -> None:
        self.rows, self.error, self.executed = rows, error, []
        self.streamed: tuple[str, object] | None = None
    @asynccontextmanager
    async def begin(self): yield
    async def execute(self, statement: object, params: object = None) -> None:
        self.executed.append((str(statement), params))
        if self.error: raise self.error
    async def stream(self, statement: object, params: object = None) -> StreamResult:
        # Mirrors AsyncConnection.stream, which binds parameters alongside the
        # statement; a compiled metric relies on that second argument.
        self.streamed = (str(statement), params)
        if self.error: raise self.error
        return StreamResult(self.rows)


class Database:
    def __init__(self, connection: Connection) -> None: self.connection_value = connection
    @asynccontextmanager
    async def connection(self): yield self.connection_value


@pytest.mark.asyncio
async def test_executor_enforces_row_and_byte_limits_before_returning_results() -> None:
    connection = Connection([["one"], ["two"], ["three"]])
    result = await AnalyticsSQLExecutor(Database(connection), AnalyticsQueryLimits(max_result_rows=2, max_result_bytes=100, timeout_seconds=1)).execute("SELECT value FROM orders", referenced_tables=["orders"])  # type: ignore[arg-type]
    assert result.rows == [["one"], ["two"]] and result.truncated
    assert any("READ ONLY" in statement for statement, _ in connection.executed)

    byte_limited = await AnalyticsSQLExecutor(Database(Connection([["x" * 100]])), AnalyticsQueryLimits(max_result_rows=2, max_result_bytes=10, timeout_seconds=1)).execute("SELECT value FROM orders", referenced_tables=["orders"])  # type: ignore[arg-type]
    assert byte_limited.rows == [] and byte_limited.truncated


@pytest.mark.asyncio
async def test_executor_maps_timeout_to_safe_failure_category() -> None:
    executor = AnalyticsSQLExecutor(Database(Connection([], RuntimeError("canceling statement due to statement timeout"))), AnalyticsQueryLimits(timeout_seconds=1))  # type: ignore[arg-type]
    with pytest.raises(AnalyticsQueryError, match="timed out") as error:
        await executor.execute("SELECT 1", referenced_tables=[])
    assert error.value.failure_category == "database_timeout"


# ------------------------------------------------- actionable failure reasons


class _Wrapped(Exception):
    """A SQLAlchemy-shaped wrapper carrying an asyncpg cause, as the driver raises."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.orig = Exception(message)


@pytest.mark.parametrize("cause,expected", [
    ("<class 'asyncpg.exceptions.UndefinedColumnError'>: column m.method_name does not exist",
     "column m.method_name does not exist"),
    ('<class \'asyncpg.exceptions.GroupingError\'>: column "m.name" must appear in the GROUP BY clause',
     'column "m.name" must appear in the GROUP BY clause'),
    ("<class 'asyncpg.exceptions.UndefinedFunctionError'>: function bogus(bigint) does not exist",
     "function bogus(bigint) does not exist"),
])
def test_a_caller_is_told_what_about_its_own_query_was_wrong(cause: str, expected: str) -> None:
    """Blind retries are what killed a run; the caller needs the failing name.

    Every message here describes the statement the caller wrote, and the schema
    is already available through describe_table, so this reveals nothing new.
    """

    from app.analytics.sql.executor import _actionable_reason

    assert _actionable_reason(_Wrapped(cause)) == expected


@pytest.mark.parametrize("cause", [
    "<class 'asyncpg.exceptions.InsufficientPrivilegeError'>: permission denied for table secrets",
    "<class 'asyncpg.exceptions.InternalServerError'>: unexpected internal state",
    "<class 'asyncpg.exceptions.ConnectionDoesNotExistError'>: connection was closed",
    "some entirely unrecognised driver failure",
])
def test_anything_not_about_the_callers_query_stays_generic(cause: str) -> None:
    """An internal or permission failure must not be echoed back."""

    from app.analytics.sql.executor import _actionable_reason

    assert _actionable_reason(_Wrapped(cause)) is None


def test_a_reason_is_bounded_to_one_line() -> None:
    from app.analytics.sql.executor import _MAX_REASON_CHARS, _actionable_reason

    sprawling = (
        "<class 'asyncpg.exceptions.UndefinedColumnError'>: column "
        + "x" * 400 + "\nHINT: something the caller need not read"
    )

    reason = _actionable_reason(_Wrapped(sprawling))

    assert reason is not None
    assert len(reason) <= _MAX_REASON_CHARS
    assert "HINT" not in reason
