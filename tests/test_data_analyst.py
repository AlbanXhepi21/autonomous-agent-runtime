"""DA3 specialist guidance and evidence-reference scenarios."""

from typing import Any

import pytest

from app.agent.models import AgentAction
from app.agent.registry import AgentRegistry
from app.core.limits import RuntimeLimits
from app.llm.base import LLMClient
from app.observability import InMemoryTraceStore, TraceEventType, TraceRecorder
from app.skills.registry import SkillRegistry
from app.tools.base import Tool
from app.tools.registry import ToolRegistry
from tests.support import make_runner


class ScriptedAnalyst(LLMClient):
    def __init__(self, actions: list[AgentAction]) -> None:
        self.actions = actions
        self.contexts: list[dict[str, object]] = []
    async def choose_action(self, *, system_prompt: str, context: dict[str, object]) -> AgentAction:
        self.contexts.append(context)
        return self.actions.pop(0)


class QueryEvidenceTool(Tool):
    @property
    def name(self) -> str: return "query_database"
    @property
    def description(self) -> str: return "Fake bounded read-only query."
    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"], "additionalProperties": False}
    async def execute(self, **arguments: Any) -> dict[str, Any]:
        if "category" in arguments["sql"]:
            return {"columns": [{"name": "category"}, {"name": "revenue"}], "rows": [["Electronics", "120.00"]], "row_count": 1, "truncated": False, "execution_ms": 2, "referenced_tables": ["order_items", "products"]}
        return {"columns": [{"name": "revenue"}], "rows": [["1000.00"]], "row_count": 1, "truncated": False, "execution_ms": 2, "referenced_tables": ["orders"]}


@pytest.mark.asyncio
async def test_analyst_can_iteratively_collect_evidence_with_stable_query_references() -> None:
    llm = ScriptedAnalyst([
        AgentAction(action_type="load_skill", reasoning_summary="Load analysis guidance.", skill_name="data_analysis"),
        AgentAction(action_type="use_tool", reasoning_summary="Measure total revenue.", tool_name="query_database", tool_arguments={"sql": "SELECT revenue FROM orders"}),
        AgentAction(action_type="use_tool", reasoning_summary="Check category explanation.", tool_name="query_database", tool_arguments={"sql": "SELECT category FROM order_items"}),
        AgentAction(action_type="finish", reasoning_summary="Evidence is sufficient.", final_answer="Revenue was $1,000; Electronics contributed $120 [query_001, query_002]."),
    ])
    tools = ToolRegistry(); tools.register(QueryEvidenceTool())
    recorder, store = TraceRecorder(InMemoryTraceStore()), None
    # Keep a direct reference to the recorder's store through get_trace.
    runner = make_runner(llm, tools, limits=RuntimeLimits(max_iterations=5), trace_recorder=recorder)
    state = await runner.run("Which category contributed to revenue?")

    assert state.completed and "query_001, query_002" in (state.final_answer or "")
    outputs = [observation.content.output for observation in state.observations if getattr(observation.content, "success", False)]
    assert outputs[0]["query_id"] == "query_001" and outputs[1]["query_id"] == "query_002"
    trace = recorder.get_trace(state.run_id)
    assert trace is not None
    finished = [event.metadata["query_id"] for event in trace.events if event.event_type is TraceEventType.DATABASE_QUERY_FINISHED]
    assert finished == ["query_001", "query_002"]


def test_data_analyst_definition_is_least_privilege_and_skill_is_business_oriented() -> None:
    definition = AgentRegistry().load_agent("data_analyst")
    instructions = SkillRegistry().load_skill("data_analysis")

    assert {"list_tables", "describe_table", "get_table_relationships", "query_database"} <= set(definition.allowed_tools)
    assert not {"python_exec", "read_file", "write_file", "run_command", "search_files"} & set(definition.allowed_tools)
    assert definition.allowed_skills == ["data_analysis", "executive_reporting"]
    assert "profitability" in instructions and "campaign" in instructions and "query_###" in instructions
    assert "KPI card requests" in instructions and "list_metrics` at most once" in instructions
