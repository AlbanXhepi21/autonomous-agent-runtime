"""V6.3 deterministic action-risk classification coverage."""

from app.agent.definition import AgentDefinition
from app.security import (
    Capability, PermissionRule, PolicyDecision, RiskCategory, RiskClassifier,
    RiskLevel, SecurityAction, SecurityEnvironment, SecurityPolicy, SecurityResource,
    SecuritySubject,
)


def subject(agent_type: str = "primary", name: str = "primary") -> SecuritySubject:
    return SecuritySubject(agent_name=name, agent_type=agent_type, run_id="run")


def action(capability: Capability, resource: str = "workspace") -> SecurityAction:
    return SecurityAction(capability=capability, tool_name="runtime_tool",
                          resource=SecurityResource(resource_type="workspace", identifier=resource))


def test_baseline_risk_levels_are_typed_and_deterministic() -> None:
    classifier = RiskClassifier()
    assert classifier.assess(subject(), action(Capability.CALCULATOR_EVALUATE)).level is RiskLevel.LOW
    assert classifier.assess(subject(), action(Capability.FILESYSTEM_WRITE)).level is RiskLevel.MEDIUM
    assert classifier.assess(subject(), action(Capability.REPOSITORY_WRITE)).level is RiskLevel.HIGH
    critical = classifier.assess(subject(), action(Capability.FILESYSTEM_WRITE, "config/production.yaml"))
    assert critical.level is RiskLevel.CRITICAL
    assert critical.category is RiskCategory.PRODUCTION_CHANGE


def test_production_environment_is_more_conservative() -> None:
    development = RiskClassifier(SecurityEnvironment.DEVELOPMENT)
    production = RiskClassifier(SecurityEnvironment.PRODUCTION)
    command = action(Capability.COMMAND_EXECUTE, "pytest")
    assert development.assess(subject(), command).level is RiskLevel.MEDIUM
    assert production.assess(subject(), command).level is RiskLevel.CRITICAL


def test_agent_permission_and_risk_are_both_required() -> None:
    definition = AgentDefinition(name="research", description="x", version="1", instructions="x", allowed_tools=[])
    policy = SecurityPolicy.primary().with_specialist(definition)
    result = policy.evaluate(subject("specialist", "research"), action(Capability.PYTHON_EXECUTE))
    assert result.decision is PolicyDecision.DENY


def test_high_risk_allowed_capability_maps_to_approval() -> None:
    policy = SecurityPolicy(
        [PermissionRule("allow.repository_write", PolicyDecision.ALLOW, capability=Capability.REPOSITORY_WRITE)],
    )
    result = policy.evaluate(subject(), action(Capability.REPOSITORY_WRITE))
    assert result.decision is PolicyDecision.REQUIRE_APPROVAL
    assert result.metadata["risk_level"] == RiskLevel.HIGH.value


def test_llm_reason_and_argument_names_do_not_lower_risk() -> None:
    classifier = RiskClassifier()
    # The classifier receives only runtime-normalized action/resource fields, not LLM prose.
    renamed_argument_action = SecurityAction(
        capability=Capability.FILESYSTEM_WRITE, tool_name="write_file",
        resource=SecurityResource(resource_type="workspace_path", identifier="src/app.py"),
    )
    assert classifier.assess(subject(), renamed_argument_action).level is RiskLevel.MEDIUM
    assert classifier.assess(subject(), renamed_argument_action).reason != "safe"


def test_unknown_actions_default_to_denial() -> None:
    policy = SecurityPolicy()
    result = policy.evaluate(subject("specialist", "unknown"), SecurityAction(capability=None, tool_name="renamed_tool"))
    assert result.decision is PolicyDecision.DENY
    assert result.metadata["risk_level"] == RiskLevel.CRITICAL.value
