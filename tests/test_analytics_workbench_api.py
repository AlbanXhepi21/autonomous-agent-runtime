"""UI1 contracts: async run lifecycle, public SSE projection, and local CORS."""

import time
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.contracts.actions import AgentAction
from app.composition import get_agent_runner, get_run_manager, get_conversation_store, get_trace_recorder
from app.orchestration.run_manager import AgentRunManager
from app.llm.contracts import LLMClient
from app.api.routes.analytics import router
from app.observability import InMemoryTraceStore, TraceRecorder
from tests.support import make_runner


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
        async def get_run(self, run_id: str): return None
        async def get_assistant_message_for_run(self, run_id: str): return None
    test_app.dependency_overrides = {
        get_agent_runner: lambda: runner,
        get_run_manager: lambda: manager,
        get_trace_recorder: lambda: recorder,
        get_conversation_store: lambda: EmptyConversationStore(),
    }
    return TestClient(test_app)


def test_create_retrieve_and_stream_a_public_run() -> None:
    with _client() as client:
        created = client.post("/api/v1/analytics/runs", json={"message": "Why did revenue fall?", "conversation_id": "conv-1"})
        assert created.status_code == 202
        run_id = created.json()["run_id"]
        for _ in range(20):
            response = client.get(f"/api/v1/analytics/runs/{run_id}")
            if response.json()["status"] != "running":
                break
            time.sleep(0.01)
        body = response.json()
        assert body["status"] == "completed"
        assert body["final_response"] == "Revenue fell because orders declined."
        stream = client.get(f"/api/v1/analytics/runs/{run_id}/events")
        assert stream.status_code == 200
        assert "event: run.started" in stream.text and "event: run.completed" in stream.text
        assert stream.text.index("event: run.started") < stream.text.index("event: agent.started") < stream.text.index("event: agent.completed") < stream.text.index("event: run.completed")
        assert "private reasoning" not in stream.text
        history = client.get(f"/api/v1/analytics/runs/{run_id}/events/history")
        assert history.status_code == 200
        assert any(event["type"] == "run.completed" for event in history.json()["items"])
        assert "private reasoning" not in history.text


def test_unknown_run_and_local_cors_are_safe() -> None:
    with _client() as client:
        missing = client.get("/api/v1/analytics/runs/missing")
        assert missing.status_code == 404
        assert missing.json()["detail"]["code"] == "unknown_run"
        cors = client.options("/api/v1/analytics/runs", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})
        assert cors.headers["access-control-allow-origin"] == "http://localhost:3000"
        denied = client.options("/api/v1/analytics/runs", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"})
        assert "access-control-allow-origin" not in denied.headers


def test_persisted_run_returns_its_durable_assistant_response_after_restart() -> None:
    with _client() as client:
        created_at = datetime.now(timezone.utc)
        store = SimpleNamespace(
            get_run=lambda run_id: _value(SimpleNamespace(
                id=run_id, conversation_id="conversation-1", status="completed",
                created_at=created_at, started_at=created_at, completed_at=created_at, metrics=None, error=None,
            )),
            get_assistant_message_for_run=lambda run_id: _value(SimpleNamespace(content="Persisted answer.")),
        )
        client.app.dependency_overrides[get_conversation_store] = lambda: store

        response = client.get("/api/v1/analytics/runs/persisted-run")

    assert response.status_code == 200
    assert response.json()["final_response"] == "Persisted answer."


async def _value(value: object) -> object:
    return value
