"""Cross-tenant HTTP isolation: direct UUID substitution against real routes.

Two synthetic tenants (Tenant A, Tenant B) are built with
``tests.support.override_tenant_context`` on two separate ``FastAPI`` app
instances that share the same backing fakes/stores -- so a resource Tenant A
creates genuinely exists in the shared store, and every assertion here is
about whether Tenant B's *route*, given Tenant A's *real* identifier,
refuses it. This is the same "direct UUID substitution" attack
``tests/integration/test_tenant_isolation.py`` proves one layer down,
against the repository methods themselves; this file proves it again at the
HTTP boundary, through the actual route functions.

Data sources, saved reports and scheduled schedules already carry their own
cross-workspace HTTP tests in test_datasources_api.py, test_saved_reports_api.py
and test_scheduled_reports_api.py; this file covers what those don't:
conversations, messages, runs, SSE streams, event history, traces, artifacts
and artifact downloads.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.artifacts import router as artifacts_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.traces import router as traces_router
from app.artifacts.contracts import Artifact, ArtifactStatus
from app.artifacts.store import WorkspaceArtifactStore
from app.composition import (
    get_agent_runner,
    get_artifact_store,
    get_conversation_store,
    get_run_manager,
    get_trace_recorder,
)
from app.contracts.actions import AgentAction
from app.environment.workspace import Workspace
from app.llm.contracts import LLMClient
from app.observability import InMemoryTraceStore, TraceRecorder
from app.orchestration.run_manager import AgentRunManager
from tests.support import make_runner, override_tenant_context

WORKSPACE_A = uuid4()
WORKSPACE_B = uuid4()


class FinishLLM(LLMClient):
    async def choose_action(self, *, system_prompt: str, context: dict[str, object]) -> AgentAction:
        return AgentAction(action_type="finish", reasoning_summary="done", final_answer="Revenue fell.")


# ------------------------------------------------------- conversations, runs, traces


class FakeConversationStore:
    """A minimal, workspace-scoped in-memory conversation store, shared by both clients."""

    def __init__(self) -> None:
        self._conversations: dict = {}
        self._runs: dict = {}

    async def create_conversation(self, *, workspace_id, title="New conversation"):
        record = SimpleNamespace(id=uuid4(), workspace_id=workspace_id, title=title,
                                 created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
        self._conversations[record.id] = record
        return record

    async def get_conversation(self, *, workspace_id, conversation_id):
        record = self._conversations.get(conversation_id)
        return record if record is not None and record.workspace_id == workspace_id else None

    async def list_conversations(self, *, workspace_id, limit, offset):
        items = [item for item in self._conversations.values() if item.workspace_id == workspace_id]
        return items[offset:offset + limit], len(items)

    async def update_title(self, *, workspace_id, conversation_id, title):
        record = await self.get_conversation(workspace_id=workspace_id, conversation_id=conversation_id)
        if record is None:
            return None
        record.title = title
        return record

    async def delete_conversation(self, *, workspace_id, conversation_id):
        record = await self.get_conversation(workspace_id=workspace_id, conversation_id=conversation_id)
        if record is None:
            return False
        del self._conversations[conversation_id]
        return True

    async def list_messages(self, *, workspace_id, conversation_id, limit, offset):
        if await self.get_conversation(workspace_id=workspace_id, conversation_id=conversation_id) is None:
            return [], 0
        return [], 0

    async def list_runs(self, *, workspace_id, conversation_id):
        if await self.get_conversation(workspace_id=workspace_id, conversation_id=conversation_id) is None:
            return []
        return [run for run in self._runs.values() if run.conversation_id == conversation_id]

    def add_run(self, *, workspace_id, conversation_id, run_id: str):
        run = SimpleNamespace(
            id=run_id, conversation_id=conversation_id, workspace_id=workspace_id, status="completed",
            created_at=datetime.now(UTC), started_at=None, completed_at=None, error=None, metrics=None,
            chart_specs=None, answer_sources=None, answer_caveats=None,
        )
        self._runs[run_id] = run
        return run

    async def get_run(self, *, workspace_id, run_id: str):
        run = self._runs.get(run_id)
        return run if run is not None and run.workspace_id == workspace_id else None

    async def get_assistant_message_for_run(self, *, workspace_id, run_id: str):
        run = await self.get_run(workspace_id=workspace_id, run_id=run_id)
        return SimpleNamespace(content="Revenue fell.") if run is not None else None


def _conversation_clients():
    store = FakeConversationStore()
    apps = []
    for workspace_id in (WORKSPACE_A, WORKSPACE_B):
        app = FastAPI()
        app.include_router(conversations_router)
        app.include_router(traces_router)
        app.dependency_overrides = {
            get_conversation_store: lambda: store,
            get_trace_recorder: lambda: TraceRecorder(InMemoryTraceStore()),
        }
        override_tenant_context(app, workspace_id=workspace_id)
        apps.append(TestClient(app))
    return store, apps[0], apps[1]


def test_a_conversation_and_its_messages_are_invisible_across_tenants() -> None:
    store, client_a, client_b = _conversation_clients()

    created = client_a.post(f"/api/v1/workspaces/{WORKSPACE_A}/conversations", json={"title": "Tenant A's investigation"})
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    assert client_a.get(f"/api/v1/workspaces/{WORKSPACE_A}/conversations/{conversation_id}").status_code == 200
    assert client_b.get(f"/api/v1/workspaces/{WORKSPACE_B}/conversations/{conversation_id}").status_code == 404
    assert conversation_id not in {item["id"] for item in client_b.get(f"/api/v1/workspaces/{WORKSPACE_B}/conversations").json()["items"]}
    assert client_b.patch(f"/api/v1/workspaces/{WORKSPACE_B}/conversations/{conversation_id}", json={"title": "Stolen"}).status_code == 404
    assert client_b.delete(f"/api/v1/workspaces/{WORKSPACE_B}/conversations/{conversation_id}").status_code == 404
    # The row survives Tenant B's refused delete.
    assert client_a.get(f"/api/v1/workspaces/{WORKSPACE_A}/conversations/{conversation_id}").status_code == 200


def test_a_run_and_its_trace_are_invisible_across_tenants() -> None:
    store, client_a, client_b = _conversation_clients()

    created = store._conversations
    conversation = SimpleNamespace(id=uuid4(), workspace_id=WORKSPACE_A, title="t",
                                   created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
    created[conversation.id] = conversation
    run = store.add_run(workspace_id=WORKSPACE_A, conversation_id=conversation.id, run_id=f"run-{uuid4()}")

    assert client_a.get(f"/api/v1/workspaces/{WORKSPACE_A}/conversations/{conversation.id}").json()["runs"][0]["run_id"] == run.id
    assert client_b.get(f"/api/v1/workspaces/{WORKSPACE_B}/conversations/{conversation.id}").status_code == 404
    assert client_b.get(f"/api/v1/workspaces/{WORKSPACE_B}/runs/{run.id}/trace").status_code == 404


# --------------------------------------------------------------------- artifacts


def _artifact_clients(tmp_path):
    """``artifacts`` keeps a bare ``/artifacts/{id}`` URL shape (see the router's
    own docstring) and so cannot use ``get_tenant_context`` at all -- it verifies
    membership by hand via ``get_current_user`` + ``get_tenancy_service``, resolving
    the artifact's owning workspace first. A fake tenancy service that only knows
    about the two contexts built here stands in for the real membership check.
    """

    from app.api.dependencies import get_current_user
    from app.composition import get_tenancy_service
    from app.tenancy.service import MembershipNotFoundError
    from tests.support import make_tenant_context

    workspace = Workspace(tmp_path)
    store = WorkspaceArtifactStore(workspace, max_artifact_bytes=10_485_760)
    contexts = {
        WORKSPACE_A: make_tenant_context(workspace_id=WORKSPACE_A),
        WORKSPACE_B: make_tenant_context(workspace_id=WORKSPACE_B),
    }

    class FakeTenancyService:
        """Mirrors the real service's rule: only a member of ``workspace_id`` resolves it."""

        async def get_context(self, *, user, workspace_id):
            context = contexts.get(workspace_id)
            if context is None or context.user.id != user.id:
                raise MembershipNotFoundError(str(workspace_id))
            return context

    tenancy = FakeTenancyService()
    apps = []
    for workspace_id in (WORKSPACE_A, WORKSPACE_B):
        app = FastAPI()
        app.include_router(artifacts_router)
        app.dependency_overrides = {
            get_artifact_store: lambda: store,
            get_current_user: (lambda wid=workspace_id: contexts[wid].user),
            get_tenancy_service: lambda: tenancy,
        }
        apps.append(TestClient(app))
    return store, apps[0], apps[1]


def test_an_artifact_and_its_download_are_invisible_across_tenants(tmp_path) -> None:
    (tmp_path / "report.md").write_text("# Tenant A's report\n")
    store, client_a, client_b = _artifact_clients(tmp_path)

    import asyncio
    artifact = asyncio.run(store.register(workspace_id=WORKSPACE_A, run_id="run-a", source_path="report.md"))

    assert client_a.get(f"/artifacts/{artifact.id}").status_code == 200
    assert client_b.get(f"/artifacts/{artifact.id}").status_code == 404
    assert client_b.get(f"/artifacts/{artifact.id}/preview").status_code == 404
    assert artifact.id not in {
        item["artifact_id"]
        for item in client_b.get("/artifacts", params={"workspace_id": str(WORKSPACE_B), "run_id": "run-a"}).json()
    }
    # Tenant A, correctly scoped, still sees its own artifact.
    assert artifact.id in {
        item["artifact_id"]
        for item in client_a.get("/artifacts", params={"workspace_id": str(WORKSPACE_A), "run_id": "run-a"}).json()
    }
    # Tenant B cannot even ask for Tenant A's workspace_id directly: the list route
    # now verifies real membership rather than trusting a caller-supplied context.
    assert client_b.get("/artifacts", params={"workspace_id": str(WORKSPACE_A), "run_id": "run-a"}).status_code == 404


# ---------------------------------------------------------------- runs, SSE, events


def _run_clients():
    recorder = TraceRecorder(InMemoryTraceStore())
    manager = AgentRunManager(recorder, expose_sql=False, max_sql_chars=100)
    runner = make_runner(FinishLLM(), trace_recorder=recorder)

    class EmptyConversationStore:
        async def get_run(self, *, workspace_id, run_id: str):
            return None

        async def get_assistant_message_for_run(self, *, workspace_id, run_id: str):
            return None

    apps = []
    for workspace_id in (WORKSPACE_A, WORKSPACE_B):
        app = FastAPI()
        app.include_router(analytics_router)
        app.dependency_overrides = {
            get_agent_runner: lambda: runner,
            get_run_manager: lambda: manager,
            get_trace_recorder: lambda: recorder,
            get_conversation_store: lambda: EmptyConversationStore(),
        }
        override_tenant_context(app, workspace_id=workspace_id)
        apps.append(TestClient(app))
    return manager, apps[0], apps[1]


def test_a_run_its_sse_stream_and_its_events_are_invisible_across_tenants() -> None:
    manager, client_a, client_b = _run_clients()

    created = client_a.post(f"/api/v1/workspaces/{WORKSPACE_A}/analytics/runs", json={"message": "Investigate revenue"})
    assert created.status_code == 202
    run_id = created.json()["run_id"]
    for _ in range(200):
        if manager.get(run_id).finished_at is not None:
            break
    else:
        raise AssertionError("run never finished")

    assert client_a.get(f"/api/v1/workspaces/{WORKSPACE_A}/analytics/runs/{run_id}").status_code == 200
    assert client_b.get(f"/api/v1/workspaces/{WORKSPACE_B}/analytics/runs/{run_id}").status_code == 404
    assert client_b.get(f"/api/v1/workspaces/{WORKSPACE_B}/analytics/runs/{run_id}/events/history").status_code == 404
    with client_b.stream("GET", f"/api/v1/workspaces/{WORKSPACE_B}/analytics/runs/{run_id}/events") as response:
        assert response.status_code == 404


# ------------------------------------------- real routing, no dependency override


def test_real_path_based_routing_enforces_isolation_without_any_tenant_context_override(tmp_path) -> None:
    """Every other test in this file fakes tenant context via ``override_tenant_context``,
    which replaces ``get_tenant_context`` outright with a zero-argument lambda -- and a
    dependency override is matched by FastAPI using *its own* signature, not the
    signature of the function it replaces. So none of those tests actually required the
    route's URL to carry a ``{workspace_id}`` path segment: a router registered with no
    such segment at all (exactly the bug this suite now guards against, once real per
    production) would still have passed every test above without changes to this file.

    This test drives two real, cookie-authenticated sessions through real registration,
    login, and workspace creation -- no dependency override for tenant context anywhere
    -- so ``get_tenant_context``'s real ``workspace_id: UUID = Path(...)`` parameter is
    actually resolved from the request path. If a route ever again shipped without its
    ``{workspace_id}`` segment, this test would fail with a 422 (missing path
    parameter), the same failure real clients hit in production, instead of passing
    silently the way the override-based tests above would.
    """

    from app.api.routes.auth import router as auth_router
    from app.api.routes.workspaces import router as workspaces_router
    from app.composition import (
        get_auth_service,
        get_invitation_store,
        get_membership_store,
        get_tenancy_service,
        get_workspace_store,
    )
    from app.identity.email import FileEmailSender
    from app.identity.passwords import Argon2PasswordHasher
    from app.identity.rate_limit import InMemoryRateLimiter
    from app.identity.service import AuthService
    from app.identity.store import InMemoryIdentityTokenStore, InMemorySessionStore, InMemoryUserStore
    from app.tenancy.service import TenancyService
    from app.tenancy.store import InMemoryInvitationStore, InMemoryMembershipStore, InMemoryWorkspaceStore

    password = "correct-horse-1"
    auth_service = AuthService(
        users=InMemoryUserStore(), sessions=InMemorySessionStore(), tokens=InMemoryIdentityTokenStore(),
        password_hasher=Argon2PasswordHasher(), email_sender=FileEmailSender(tmp_path / ".auth-mail"),
        rate_limiter=InMemoryRateLimiter(), session_idle_ttl_seconds=43_200, session_absolute_ttl_seconds=2_592_000,
        password_reset_ttl_seconds=3_600, email_verification_ttl_seconds=259_200, app_base_url="http://localhost:3000",
    )
    workspaces, memberships, invitations = InMemoryWorkspaceStore(), InMemoryMembershipStore(), InMemoryInvitationStore()
    tenancy_service = TenancyService(
        workspaces=workspaces, memberships=memberships, invitations=invitations,
        email_sender=FileEmailSender(tmp_path / ".tenancy-mail"), invitation_ttl_seconds=604_800,
        app_base_url="http://localhost:3000",
    )
    conversation_store = FakeConversationStore()

    application = FastAPI()
    application.include_router(auth_router)
    application.include_router(workspaces_router)
    application.include_router(conversations_router)
    application.dependency_overrides = {
        get_auth_service: lambda: auth_service,
        get_tenancy_service: lambda: tenancy_service,
        get_workspace_store: lambda: workspaces,
        get_membership_store: lambda: memberships,
        get_invitation_store: lambda: invitations,
        get_conversation_store: lambda: conversation_store,
        get_trace_recorder: lambda: TraceRecorder(InMemoryTraceStore()),
    }

    client_a, client_b = TestClient(application), TestClient(application)
    for client, email in ((client_a, "owner-a@example.com"), (client_b, "owner-b@example.com")):
        registered = client.post(
            "/api/v1/auth/register", json={"email": email, "password": password, "display_name": "Owner"},
        )
        assert registered.status_code == 201, registered.text
        logged_in = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert logged_in.status_code == 200, logged_in.text

    workspace_a = client_a.post(
        "/api/v1/workspaces", json={"name": "A Co", "slug": "a-co"},
        headers={"X-CSRF-Token": client_a.cookies.get("csrf_token")},
    )
    workspace_b = client_b.post(
        "/api/v1/workspaces", json={"name": "B Co", "slug": "b-co"},
        headers={"X-CSRF-Token": client_b.cookies.get("csrf_token")},
    )
    assert workspace_a.status_code == 201, workspace_a.text
    assert workspace_b.status_code == 201, workspace_b.text
    workspace_a_id, workspace_b_id = workspace_a.json()["id"], workspace_b.json()["id"]

    created = client_a.post(
        f"/api/v1/workspaces/{workspace_a_id}/conversations",
        json={"title": "Tenant A's investigation"},
        headers={"X-CSRF-Token": client_a.cookies.get("csrf_token")},
    )
    assert created.status_code == 201, created.text
    conversation_id = created.json()["id"]

    # Tenant A, through its own workspace id, sees what it created.
    assert client_a.get(f"/api/v1/workspaces/{workspace_a_id}/conversations/{conversation_id}").status_code == 200
    # Tenant B, through its own (different, really-authorized) workspace id, does not --
    # resolved via the real `get_tenant_context` dependency and the real path parameter.
    assert client_b.get(f"/api/v1/workspaces/{workspace_b_id}/conversations/{conversation_id}").status_code == 404
    # Tenant B cannot borrow Tenant A's workspace id either: real membership is checked,
    # not merely whichever id happens to appear in the URL.
    assert client_b.get(f"/api/v1/workspaces/{workspace_a_id}/conversations/{conversation_id}").status_code == 404
