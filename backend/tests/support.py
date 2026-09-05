"""Shared test doubles and runtime construction helpers.

These live outside ``conftest.py`` so tests can import the names directly;
importing from a conftest module is discouraged by pytest. ``conftest.py``
exposes the same helpers as fixtures for tests that prefer injection.

``make_runner`` exists so that the ``AgentRunner`` signature is referenced in
one place rather than at every construction site.
"""

import uuid
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from app.contracts.actions import AgentAction
from app.datasources.service import DataSourceOnboardingError
from app.identity.contracts import User
from app.llm.contracts import LLMClient
from app.runtime.runner import AgentRunner
from app.skills.registry import SkillRegistry
from app.tenancy.context import TenantContext
from app.tenancy.contracts import Membership, MembershipStatus, Role, Workspace
from app.tenancy.permissions import ROLE_PERMISSIONS
from app.tools.registry import ToolRegistry

#: Resolved here so tests can move between directories without recounting parents.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
#: The backend and the Workbench are siblings; cross-boundary checks need both.
REPO_ROOT = BACKEND_ROOT.parent


class ScriptedLLM(LLMClient):
    """Return a fixed sequence of actions without making network calls.

    The last action repeats once the script is exhausted, so a test only needs
    to script the actions it actually asserts on. Each context and system prompt
    handed to the provider is retained on ``contexts`` and ``prompts``, for
    assertions about what the runtime chose to expose to the model.
    """

    def __init__(self, actions: AgentAction | list[AgentAction]) -> None:
        self._actions = [actions] if isinstance(actions, AgentAction) else list(actions)
        if not self._actions:
            raise ValueError("ScriptedLLM requires at least one action.")
        self.calls = 0
        self.contexts: list[dict[str, Any]] = []
        self.prompts: list[str] = []

    async def choose_action(
        self, *, system_prompt: str, context: dict[str, Any]
    ) -> AgentAction:
        self.prompts.append(system_prompt)
        self.contexts.append(context)
        action = self._actions[min(self.calls, len(self._actions) - 1)]
        self.calls += 1
        return action


def make_runner(
    llm: LLMClient,
    tool_registry: ToolRegistry | None = None,
    skill_registry: SkillRegistry | None = None,
    **overrides: Any,
) -> AgentRunner:
    """Build an ``AgentRunner`` with empty registries unless a test supplies its own.

    Every keyword the runtime accepts passes straight through, so a test states
    only the collaborators it actually exercises.
    """

    return AgentRunner(
        llm_client=llm,
        tool_registry=tool_registry if tool_registry is not None else ToolRegistry(),
        skill_registry=skill_registry if skill_registry is not None else SkillRegistry(),
        **overrides,
    )


def make_tenant_context(
    *, workspace_id: uuid.UUID | None = None, role: Role = Role.OWNER,
    default_timezone: str = "UTC", default_locale: str = "en-US", default_currency: str = "USD",
) -> TenantContext:
    """Build a self-consistent ``TenantContext`` for tests that call a route

    function directly rather than through an authenticated ``TestClient``.
    The ``default_*`` overrides let a test simulate two workspaces with
    different regional settings sharing the same backing fakes.
    """

    now = datetime.now(timezone.utc)
    workspace_id = workspace_id or uuid.uuid4()
    user_id = uuid.uuid4()
    return TenantContext(
        user=User(
            id=user_id, email="test@example.com", display_name="Test User", password_hash="",
            is_active=True, email_verified=True, created_at=now, updated_at=now,
        ),
        workspace=Workspace(
            id=workspace_id, name="Test Workspace", slug=f"test-{workspace_id}", is_active=True,
            default_timezone=default_timezone, default_locale=default_locale, default_currency=default_currency,
            created_at=now, updated_at=now,
        ),
        membership=Membership(
            id=uuid.uuid4(), user_id=user_id, workspace_id=workspace_id, role=role,
            status=MembershipStatus.ACTIVE, joined_at=now, created_at=now, updated_at=now,
        ),
        role=role,
        permissions=ROLE_PERMISSIONS[role],
    )


def override_tenant_context(
    app: Any, *, workspace_id: uuid.UUID | None = None, role: Role = Role.OWNER,
    default_timezone: str = "UTC", default_locale: str = "en-US", default_currency: str = "USD",
) -> TenantContext:
    """Make ``app`` (a FastAPI instance) resolve every tenant-scoped route to
    one fixed, fully-permissioned ``TenantContext``, bypassing real cookie
    auth and CSRF entirely.

    Real login/CSRF mechanics are already proven end to end by
    ``tests/api/test_auth_api.py`` and ``tests/api/test_workspaces_api.py``;
    business-route tests only need a stable, known tenant to assert against.
    ``get_tenant_context`` is the one dependency every ``require_permission``
    closure resolves through (FastAPI matches overrides by the dependency
    callable, regardless of how deep it is referenced), so overriding it here
    covers every route in the app no matter which permission it requires.
    Two calls with different ``workspace_id`` values on two separate ``app``
    instances simulate two different tenants sharing the same backing fakes.
    """

    from app.api.dependencies import get_tenant_context, require_csrf

    context = make_tenant_context(
        workspace_id=workspace_id, role=role, default_timezone=default_timezone,
        default_locale=default_locale, default_currency=default_currency,
    )
    app.dependency_overrides[get_tenant_context] = lambda: context
    app.dependency_overrides[require_csrf] = lambda: None
    return context


class FakeTenancyService:
    """The one method ``app.api.routes.artifacts`` calls directly (not through
    ``get_tenant_context``, since that route has no ``{workspace_id}`` path
    segment to resolve one from -- see the module docstring there). Returns
    the same self-consistent ``TenantContext`` ``make_tenant_context`` would
    build through the normal dependency, so a direct call to
    ``download_artifact``/``preview_artifact``/``list_artifacts`` sees the
    same shape of context a real request would.
    """

    def __init__(self, *, role: Role = Role.OWNER) -> None:
        self._role = role

    async def get_context(self, *, user: User, workspace_id: uuid.UUID) -> TenantContext:
        return make_tenant_context(workspace_id=workspace_id, role=self._role)


def make_artifact_route_caller(*, workspace_id: uuid.UUID | None = None, role: Role = Role.OWNER):
    """Return ``(user, tenancy)`` for calling an ``artifacts.py`` route function
    directly, matching its ``user: User = Depends(get_current_user)`` /
    ``tenancy: TenancyService = Depends(get_tenancy_service)`` signature --
    the replacement for passing a bare ``TenantContext`` positionally, which
    is what these routes took before they were changed to resolve the owning
    workspace from the artifact itself (see ``app/api/routes/artifacts.py``).
    """

    context = make_tenant_context(workspace_id=workspace_id, role=role)
    return context.user, FakeTenancyService(role=role)


class _NoDataSourceService:
    """Stand-in for ``DataSourceOnboardingService`` that always reports no
    active connection, so ``run_agent`` falls back to the injected runner."""

    async def active_connection_runtime(self, *, workspace_id: UUID) -> Any:
        raise DataSourceOnboardingError("No active data source for this workspace.")


async def run_agent_directly(request: Any, runner: AgentRunner, *, context: TenantContext | None = None) -> Any:
    """Call the ``/agent/run`` route function without an HTTP layer.

    Supplies a synthetic tenant context and a data-source service that always
    reports "no active connection", so the route falls back to using
    ``runner`` exactly as it did before workspace scoping existed.
    """

    from app.api.routes.agent import run_agent

    return await run_agent(
        request,
        context or make_tenant_context(),
        runner,
        _NoDataSourceService(),
        None,
        None,
    )


def logged_event(records: "Iterable[Any]", event: str) -> dict[str, Any]:
    """Return the fields of one logged event, naming it when it is absent.

    Reading caplog with next() and no default turns a missing event into
    StopIteration, and inside an async test into "coroutine raised
    StopIteration", which says nothing about what was expected.
    """

    for record in records:
        if record.getMessage() == event:
            return record.event_fields
    raise AssertionError(f"No {event!r} event was logged.")
