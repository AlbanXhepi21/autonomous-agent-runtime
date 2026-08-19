"""Strongly typed, provider-independent security models."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PolicyDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class Capability(StrEnum):
    CALCULATOR_EVALUATE = "calculator.evaluate"
    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    COMMAND_EXECUTE = "command.execute"
    PYTHON_EXECUTE = "python.execute"
    REPOSITORY_READ = "repository.read"
    REPOSITORY_WRITE = "repository.write"
    ARTIFACT_CREATE = "artifact.create"
    AGENT_DELEGATE = "agent.delegate"
    WEB_SEARCH = "web.search"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(StrEnum):
    READ_ONLY = "read_only"
    LOCAL_MODIFICATION = "local_modification"
    CODE_EXECUTION = "code_execution"
    DESTRUCTIVE = "destructive"
    EXTERNAL_SIDE_EFFECT = "external_side_effect"
    CREDENTIAL_ACCESS = "credential_access"
    PRODUCTION_CHANGE = "production_change"
    UNKNOWN = "unknown"


class SecurityEnvironment(StrEnum):
    UNKNOWN = "unknown"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ContentTrust(StrEnum):
    """Instruction provenance, distinct from factual reliability."""

    TRUSTED_RUNTIME = "trusted_runtime"
    TRUSTED_AGENT_DEFINITION = "trusted_agent_definition"
    USER_INPUT = "user_input"
    UNTRUSTED_EXTERNAL = "untrusted_external"
    TOOL_OUTPUT = "tool_output"
    RETRIEVED_MEMORY = "retrieved_memory"


class UntrustedContent(BaseModel):
    """External evidence that must never be interpreted as runtime instruction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    content: Any
    source: str = Field(min_length=1, max_length=512)
    source_type: str = Field(min_length=1, max_length=64)
    trust: ContentTrust = ContentTrust.UNTRUSTED_EXTERNAL
    metadata: dict[str, Any] = Field(default_factory=dict)
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SecuritySubject(BaseModel):
    """Identity supplied by runtime state, never an agent action payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_name: str = Field(min_length=1)
    agent_type: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    parent_run_id: str | None = None
    delegation_depth: int = Field(default=0, ge=0)


class SecurityResource(BaseModel):
    """A bounded description of the target of an action."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    resource_type: str = Field(min_length=1)
    identifier: str = Field(min_length=1, max_length=512)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityAction(BaseModel):
    """A normalized runtime action sent to the policy layer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    capability: Capability | None
    resource: SecurityResource | None = None
    tool_name: str | None = None


class PolicyResult(BaseModel):
    """Safe, structured result of one deterministic policy evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: PolicyDecision
    reason: str
    policy_id: str
    capability: Capability | None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RiskAssessment(BaseModel):
    """Deterministic classification produced only from runtime-owned inputs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    level: RiskLevel
    category: RiskCategory
    reason: str
    rule_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
