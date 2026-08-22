"""V6.5 runtime-side credential boundary coverage."""

from typing import Any

import pytest

from app.runtime.context import ContextBuilder
from app.contracts.specialists import AgentDefinition
from app.runtime.state import AgentState
from app.core.logging import safe_error_message, safe_log_value
from app.core.limits import RuntimeLimits
from app.environment.commands import CommandExecutor
from app.environment.python import PythonExecutor
from app.environment.workspace import Workspace
from app.artifacts.store import WorkspaceArtifactStore
from app.memory.writing import MemoryCandidate, MemoryCategory, MemoryPolicy
from app.memory.records import MemoryType
from app.security import EnvironmentCredentialProvider, SecretReference, SecurityPolicy, SecuritySubject
from app.security.approvals import safe_argument_summary
from app.skills.registry import SkillRegistry
from app.tools.base import Tool
from app.tools.execution import ToolExecutor
from app.tools.registry import ToolRegistry

SECRET = "ghp_abcdefghijklmnopqrstuvwxyz123456"


class CredentialTool(Tool):
    """A trusted integration resolves its logical credential internally."""
    def __init__(self, provider: EnvironmentCredentialProvider) -> None: self._provider = provider
    @property
    def name(self) -> str: return "calculator"
    @property
    def description(self) -> str: return "Call a trusted service without exposing credentials."
    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
    async def execute(self, **_: Any) -> dict[str, str]:
        assert self._provider.resolve(SecretReference(name="github.default")) == SECRET
        return {"status": "service called", "credential": "github.default"}


@pytest.mark.asyncio
async def test_secret_resolves_only_inside_trusted_tool_and_not_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", SECRET)
    provider = EnvironmentCredentialProvider()
    registry = ToolRegistry(); registry.register(CredentialTool(provider))
    result = await ToolExecutor(registry).execute("calculator", {})
    context = ContextBuilder(registry, SkillRegistry(), RuntimeLimits()).build(AgentState(goal="Call GitHub"))

    assert result.success and result.output["credential"] == "github.default"
    assert SECRET not in str(context)
    assert SECRET not in str(result.model_dump())


def test_known_secrets_are_redacted_from_logs_errors_and_approval_display(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", SECRET)
    EnvironmentCredentialProvider().resolve(SecretReference(name="github.default"))

    assert safe_log_value(f"failure {SECRET}") == "failure [REDACTED]"
    assert safe_error_message(f"token failed {SECRET}") == "token failed [REDACTED]"
    summary = safe_argument_summary({"credential": "github.default", "value": SECRET})
    assert summary["credential"] == "github.default"
    assert summary["value"] == "[REDACTED]"


def test_command_and_python_child_environments_exclude_host_secrets(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    for name in ("OPENAI_API_KEY", "DATABASE_URL", "GITHUB_TOKEN", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.setenv(name, SECRET)
    command_env = CommandExecutor._safe_environment()
    python_env = PythonExecutor._safe_environment()
    for name in ("OPENAI_API_KEY", "DATABASE_URL", "GITHUB_TOKEN", "AWS_SECRET_ACCESS_KEY"):
        assert name not in command_env and name not in python_env


def test_memory_and_artifacts_reject_obvious_credentials(tmp_path: Any) -> None:
    candidate = MemoryCandidate(content=f"token={SECRET}", memory_type=MemoryType.LONG_TERM,
                                category=MemoryCategory.LESSON, reason="x", source_run_id="run")
    assert MemoryPolicy().rejection_reason(candidate) == "credential_material"

    workspace = Workspace(tmp_path)
    (tmp_path / ".env").write_text(f"GITHUB_TOKEN={SECRET}")
    with pytest.raises(ValueError, match="Sensitive credential"):
        WorkspaceArtifactStore(workspace).register(run_id="run", source_path=".env")


@pytest.mark.asyncio
async def test_specialist_can_use_credential_backed_tool_without_receiving_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", SECRET)
    registry = ToolRegistry(); registry.register(CredentialTool(EnvironmentCredentialProvider()))
    engineer = AgentDefinition(name="software_engineer", description="x", version="1", instructions="x", allowed_tools=["calculator"])
    policy = SecurityPolicy.primary().with_specialist(engineer)
    subject = SecuritySubject(agent_name="software_engineer", agent_type="specialist", run_id="child", parent_run_id="parent", delegation_depth=1)
    allowed = await ToolExecutor(registry, security_policy=policy).execute("calculator", {}, subject=subject)
    denied = await ToolExecutor(registry, security_policy=policy).execute(
        "calculator", {}, subject=SecuritySubject(agent_name="research", agent_type="specialist", run_id="child")
    )
    assert allowed.success and SECRET not in str(allowed.model_dump())
    assert not denied.success
