"""UI1 contracts: async run lifecycle, public SSE projection, and local CORS.

Tenant auth is faked via ``tests.support.override_tenant_context`` rather than
a real cookie session -- that flow is already proven end to end by
test_auth_api.py. Every run created through the ``/runs`` route is stamped
with the fixed synthetic workspace, so same-tenant GET/SSE access against it
still succeeds under the new ``run.workspace_id != context.workspace.id``
check.
"""

import time
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.api.routes.analytics import router
from app.composition import get_agent_runner, get_conversation_store, get_run_manager, get_trace_recorder
from app.contracts.actions import AgentAction
from app.llm.contracts import LLMClient
from app.observability import InMemoryTraceStore, TraceRecorder
from app.orchestration.run_manager import AgentRunManager
from tests.support import make_runner, override_tenant_context

WORKSPACE_ID = uuid4()


class FinishLLM(LLMClient):
    async def choose_action(self, *, system_prompt: str, context: dict[str, object]) -> AgentAction:
        return AgentAction(action_type="finish", reasoning_summary="private reasoning must never leave runtime", final_answer="Revenue fell because orders declined.")


def _client() -> TestClient:
    recorder = TraceRecorder(InMemoryTraceStore())
    manager = AgentRunManager(recorder, expose_sql=False, max_sql_chars=100)
    runner = make_runner(FinishLLM(), trace_recorder=recorder)
    test_app = FastAPI()
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Last-Event-ID"],
    )
    test_app.include_router(router)
    class EmptyConversationStore:
        async def get_run(self, *, workspace_id, run_id: str): return None
        async def get_assistant_message_for_run(self, *, workspace_id, run_id: str): return None
    test_app.dependency_overrides = {
        get_agent_runner: lambda: runner,
        get_run_manager: lambda: manager,
        get_trace_recorder: lambda: recorder,
        get_conversation_store: lambda: EmptyConversationStore(),
    }
    override_tenant_context(test_app, workspace_id=WORKSPACE_ID)
    return TestClient(test_app)


def test_create_retrieve_and_stream_a_public_run() -> None:
    with _client() as client:
        created = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs", json={"message": "Why did revenue fall?", "conversation_id": "conv-1"})
        assert created.status_code == 202
        run_id = created.json()["run_id"]
        for _ in range(20):
            response = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/{run_id}")
            if response.json()["status"] != "running":
                break
            time.sleep(0.01)
        body = response.json()
        assert body["status"] == "completed"
        assert body["final_response"] == "Revenue fell because orders declined."
        stream = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/{run_id}/events")
        assert stream.status_code == 200
        assert "event: run.started" in stream.text and "event: run.completed" in stream.text
        assert stream.text.index("event: run.started") < stream.text.index("event: agent.started") < stream.text.index("event: agent.completed") < stream.text.index("event: run.completed")
        assert "private reasoning" not in stream.text
        history = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/{run_id}/events/history")
        assert history.status_code == 200
        assert any(event["type"] == "run.completed" for event in history.json()["items"])
        assert "private reasoning" not in history.text


def test_unknown_run_and_local_cors_are_safe() -> None:
    with _client() as client:
        missing = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/missing")
        assert missing.status_code == 404
        assert missing.json()["detail"]["code"] == "unknown_run"
        cors = client.options(f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})
        assert cors.headers["access-control-allow-origin"] == "http://localhost:3000"
        denied = client.options(f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"})
        assert "access-control-allow-origin" not in denied.headers


def test_persisted_run_returns_its_durable_assistant_response_after_restart() -> None:
    with _client() as client:
        created_at = datetime.now(timezone.utc)
        store = SimpleNamespace(
            get_run=lambda *, workspace_id, run_id: _value(SimpleNamespace(
                id=run_id, conversation_id="conversation-1", status="completed",
                created_at=created_at, started_at=created_at, completed_at=created_at, metrics=None, error=None,
            )),
            get_assistant_message_for_run=lambda *, workspace_id, run_id: _value(SimpleNamespace(content="Persisted answer.")),
        )
        client.app.dependency_overrides[get_conversation_store] = lambda: store

        response = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/persisted-run")

    assert response.status_code == 200
    assert response.json()["final_response"] == "Persisted answer."


def test_persisted_citations_survive_the_trace_that_minted_them() -> None:
    # "query_003" is numbered against a process-local trace, so a stored answer
    # keeping only that reference would resolve to nothing here. The registry is
    # written out in full, and this is the request that proves it.
    with _client() as client:
        created_at = datetime.now(timezone.utc)
        store = SimpleNamespace(
            get_run=lambda *, workspace_id, run_id: _value(SimpleNamespace(
                id=run_id, conversation_id="conversation-1", status="completed",
                created_at=created_at, started_at=created_at, completed_at=created_at,
                metrics=None, error=None, chart_specs=None,
                answer_sources=[{
                    "id": "query_003", "kind": "database_query", "run_id": run_id,
                    "label": "Revenue by category", "referenced_tables": ["orders", "order_items"],
                    "row_count": 12, "truncated": False,
                    "executed_at": created_at.isoformat(),
                }],
            )),
            get_assistant_message_for_run=lambda *, workspace_id, run_id: _value(SimpleNamespace(content="Persisted answer.")),
        )
        client.app.dependency_overrides[get_conversation_store] = lambda: store

        response = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/persisted-run")

    assert response.status_code == 200
    source = response.json()["sources"][0]
    assert source["id"] == "query_003"
    assert source["label"] == "Revenue by category"
    assert source["referenced_tables"] == ["orders", "order_items"]


def test_an_answer_citing_nothing_reports_an_empty_registry() -> None:
    with _client() as client:
        created = client.post(f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs", json={"message": "Why did revenue fall?", "conversation_id": "conv-1"})
        run_id = created.json()["run_id"]
        for _ in range(20):
            response = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/{run_id}")
            if response.json()["status"] != "running":
                break
            time.sleep(0.01)

    assert response.json()["sources"] == []


async def _value(value: object) -> object:
    return value


def test_persisted_caveats_are_returned_with_a_reloaded_run() -> None:
    with _client() as client:
        created_at = datetime.now(timezone.utc)
        store = SimpleNamespace(
            get_run=lambda *, workspace_id, run_id: _value(SimpleNamespace(
                id=run_id, conversation_id="conversation-1", status="completed",
                created_at=created_at, started_at=created_at, completed_at=created_at,
                metrics=None, error=None, chart_specs=None, answer_sources=None,
                answer_caveats=["August 2026 is a partial month."],
            )),
            get_assistant_message_for_run=lambda *, workspace_id, run_id: _value(SimpleNamespace(content="Persisted answer.")),
        )
        client.app.dependency_overrides[get_conversation_store] = lambda: store

        response = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/persisted-run")

    assert response.status_code == 200
    assert response.json()["caveats"] == ["August 2026 is a partial month."]


def test_a_run_stored_before_caveats_existed_reports_an_empty_list() -> None:
    """The column is null on older rows, and the attribute is absent on older readers."""

    with _client() as client:
        created_at = datetime.now(timezone.utc)
        store = SimpleNamespace(
            get_run=lambda *, workspace_id, run_id: _value(SimpleNamespace(
                id=run_id, conversation_id="conversation-1", status="completed",
                created_at=created_at, started_at=created_at, completed_at=created_at,
                metrics=None, error=None, chart_specs=None, answer_sources=None,
            )),
            get_assistant_message_for_run=lambda *, workspace_id, run_id: _value(SimpleNamespace(content="Persisted answer.")),
        )
        client.app.dependency_overrides[get_conversation_store] = lambda: store

        response = client.get(f"/api/v1/workspaces/{WORKSPACE_ID}/analytics/runs/persisted-run")

    assert response.status_code == 200
    assert response.json()["caveats"] == []
