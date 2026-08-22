"""DA1 coverage for safe metadata discovery boundaries."""


import pytest

from app.contracts.specialists import AgentDefinition
from app.analytics.models import DatabaseColumn, DatabaseSchemaSummary, DatabaseTable, ForeignKeyRelationship, TableDescription
from app.config import Settings
from app.observability import InMemoryTraceStore, TraceEventType, TraceRecorder
from app.security import Capability, PolicyDecision, SecurityAction, SecurityPolicy, SecuritySubject
from app.tools.database import DescribeTableTool, GetTableRelationshipsTool, ListTablesTool, SearchSchemaTool
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry


class Inspector:
    def __init__(self) -> None:
        self.relationship = ForeignKeyRelationship(source_table="orders", source_column="customer_id", target_table="customers", target_column="id", source_schema="public", target_schema="public")
        self.orders = TableDescription(name="orders", schema="public", columns=[DatabaseColumn(name="id", data_type="BIGINT", nullable=False, primary_key=True), DatabaseColumn(name="customer_id", data_type="BIGINT", nullable=False, foreign_key_target="customers.id")], primary_key=["id"], foreign_keys=[self.relationship])

    async def list_tables(self) -> DatabaseSchemaSummary:
        return DatabaseSchemaSummary(schemas=["public"], tables=[DatabaseTable(name="customers", schema="public"), DatabaseTable(name="orders", schema="public")])

    async def describe_table(self, name: str) -> TableDescription:
        if name != "orders":
            from app.analytics.inspector import UnknownAnalyticsTableError
            raise UnknownAnalyticsTableError(f"Unknown table: {name}.")
        return self.orders

    async def get_relationships(self, names: list[str] | None = None) -> list[ForeignKeyRelationship]:
        return [self.relationship] if names in (None, ["orders"]) else []

    async def search_schema(self, query: str) -> list[DatabaseTable]:
        return [DatabaseTable(name="orders", schema="public")] if query.lower() in {"order", "customer"} else []


def tools() -> ToolRegistry:
    inspector = Inspector()
    registry = ToolRegistry()
    registry.register(ListTablesTool(inspector))  # type: ignore[arg-type]
    registry.register(DescribeTableTool(inspector))  # type: ignore[arg-type]
    registry.register(GetTableRelationshipsTool(inspector))  # type: ignore[arg-type]
    registry.register(SearchSchemaTool(inspector))  # type: ignore[arg-type]
    return registry


@pytest.mark.asyncio
async def test_metadata_tools_return_schema_not_rows() -> None:
    registry = tools()
    executor = ToolExecutor(registry)
    listed = await executor.execute("list_tables", {})
    described = await executor.execute("describe_table", {"table_name": "orders"})
    relationships = await executor.execute("get_table_relationships", {"table_name": "orders"})

    assert listed.success and listed.output == [{"name": "customers", "schema": "public"}, {"name": "orders", "schema": "public"}]
    assert described.success and described.output["primary_key"] == ["id"]
    assert described.output["columns"][1]["foreign_key_target"] == "customers.id"
    assert relationships.success and relationships.output[0]["target_table"] == "customers"


@pytest.mark.asyncio
async def test_unknown_table_is_safe_and_schema_events_are_traced() -> None:
    registry, store = tools(), InMemoryTraceStore()
    recorder = TraceRecorder(store)
    recorder.start_run(run_id="analytics-run", parent_run_id=None, agent_name="data_analyst", agent_type="specialist", goal="inspect")
    policy = SecurityPolicy.primary().with_specialist(AgentDefinition(name="data_analyst", description="x", version="1", instructions="x", allowed_tools=["describe_table"]))
    executor = ToolExecutor(registry, security_policy=policy, trace_recorder=recorder)
    subject = SecuritySubject(agent_name="data_analyst", agent_type="specialist", run_id="analytics-run")
    result = await executor.execute("describe_table", {"table_name": "missing"}, run_id="analytics-run", subject=subject)

    assert not result.success and result.error == "Unknown table: missing."
    trace = store.get("analytics-run")
    assert trace is not None
    event = next(event for event in trace.events if event.event_type is TraceEventType.DATABASE_TABLE_DESCRIBED)
    assert event.metadata["agent"] == "data_analyst" and event.metadata["table_names"] == ["missing"]


def test_schema_capability_is_explicit_and_other_specialists_are_denied() -> None:
    policy = SecurityPolicy.primary().with_specialist(AgentDefinition(name="data_analyst", description="x", version="1", instructions="x", allowed_tools=["list_tables"]))
    action = SecurityAction(capability=Capability.DATABASE_SCHEMA_READ)
    assert policy.evaluate(SecuritySubject(agent_name="data_analyst", agent_type="specialist", run_id="r"), action).decision is PolicyDecision.ALLOW
    assert policy.evaluate(SecuritySubject(agent_name="research", agent_type="specialist", run_id="r"), action).decision is PolicyDecision.DENY


def test_analytics_database_configuration_is_separate_and_hidden() -> None:
    settings = Settings(_env_file=None, analytics_database_url="postgresql+asyncpg://user:password@host/db")
    assert settings.analytics_database_url == "postgresql+asyncpg://user:password@host/db"
    assert "password" not in repr(settings)
