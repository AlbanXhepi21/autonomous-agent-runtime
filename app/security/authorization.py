"""Deterministic authorization policy for normalized agent actions."""

from dataclasses import dataclass
from collections.abc import Iterable

from app.contracts.specialists import AgentDefinition
from app.security.contracts import Capability, PolicyDecision, PolicyResult, RiskAssessment, RiskLevel, SecurityAction, SecuritySubject
from app.security.permissions import capabilities_for_tools
from app.security.risk import RiskClassifier


@dataclass(frozen=True, slots=True)
class PermissionRule:
    """One exact semantic capability grant or denial."""

    identifier: str
    decision: PolicyDecision
    capability: Capability | None = None
    agent_name: str | None = None
    agent_type: str | None = None
    reason: str = "Action is governed by runtime security policy."

    def matches(self, subject: SecuritySubject, action: SecurityAction) -> bool:
        return (
            (self.agent_name is None or self.agent_name == subject.agent_name)
            and (self.agent_type is None or self.agent_type == subject.agent_type)
            and (self.capability is None or self.capability == action.capability)
        )


class SecurityPolicy:
    """Evaluate runtime identities and semantic capabilities without LLM input."""

    def __init__(
        self, rules: Iterable[PermissionRule] = (), *, risk_classifier: RiskClassifier | None = None,
        risk_decisions: dict[RiskLevel, PolicyDecision] | None = None,
    ) -> None:
        self._rules = tuple(rules)
        self._risk_classifier = risk_classifier or RiskClassifier()
        self._risk_decisions = risk_decisions or {
            RiskLevel.LOW: PolicyDecision.ALLOW,
            RiskLevel.MEDIUM: PolicyDecision.ALLOW,
            RiskLevel.HIGH: PolicyDecision.REQUIRE_APPROVAL,
            RiskLevel.CRITICAL: PolicyDecision.DENY,
        }

    def evaluate(self, subject: SecuritySubject, action: SecurityAction) -> PolicyResult:
        assessment = self._risk_classifier.assess(subject, action)
        for rule in self._rules:
            if rule.matches(subject, action):
                # Compatibility for runtime-owned test/internal tools that have not yet
                # been normalized; unknown specialist capabilities still default deny.
                if action.capability is None and subject.agent_type in {"primary", "system"}:
                    return self._result(PolicyDecision.ALLOW, rule.reason, rule.identifier, action, assessment)
                if rule.decision is not PolicyDecision.ALLOW:
                    return self._result(rule.decision, rule.reason, rule.identifier, action, assessment)
                decision = self._risk_decisions[assessment.level]
                return PolicyResult(
                    decision=decision,
                    reason=(assessment.reason if decision is not PolicyDecision.ALLOW else rule.reason),
                    policy_id=(assessment.rule_id if decision is not PolicyDecision.ALLOW else rule.identifier),
                    capability=action.capability, metadata=self._risk_metadata(assessment),
                )
        if action.capability is None:
            return self._result(PolicyDecision.DENY, "Requested capability is not recognized.",
                                "security.unknown_capability", action, assessment)
        return self._result(PolicyDecision.DENY, "This agent is not permitted to use this capability.",
                            "security.default_deny", action, assessment)

    @staticmethod
    def _risk_metadata(assessment: RiskAssessment) -> dict[str, object]:
        return {"risk_level": assessment.level.value, "risk_category": assessment.category.value,
                "risk_rule": assessment.rule_id, "risk_metadata": assessment.metadata}

    def _result(self, decision: PolicyDecision, reason: str, policy_id: str,
                action: SecurityAction, assessment: RiskAssessment) -> PolicyResult:
        return PolicyResult(decision=decision, reason=reason, policy_id=policy_id,
                            capability=action.capability, metadata=self._risk_metadata(assessment))

    @classmethod
    def primary(cls, *, risk_classifier: RiskClassifier | None = None) -> "SecurityPolicy":
        """Policy for the runtime's parent agent; tool boundaries remain authoritative."""

        return cls([
            PermissionRule("security.primary.allow", PolicyDecision.ALLOW, agent_type="primary"),
            PermissionRule("security.system.allow", PolicyDecision.ALLOW, agent_type="system"),
        ], risk_classifier=risk_classifier)

    def with_specialist(self, definition: AgentDefinition) -> "SecurityPolicy":
        """Add only capabilities explicitly granted by an on-disk definition."""

        rules = list(self._rules)
        for capability in capabilities_for_tools(definition.allowed_tools):
            rules.append(PermissionRule(
                identifier=f"security.specialist.{definition.name}.{capability.value}",
                decision=PolicyDecision.ALLOW, capability=capability,
                agent_name=definition.name, agent_type="specialist",
                reason="Capability is granted by this specialist definition.",
            ))
        return SecurityPolicy(rules, risk_classifier=self._risk_classifier, risk_decisions=self._risk_decisions)

    def with_human_approval_gates(
        self,
        capabilities: Iterable[Capability] = (
            Capability.FILESYSTEM_WRITE,
            Capability.COMMAND_EXECUTE,
            Capability.PYTHON_EXECUTE,
            Capability.ARTIFACT_CREATE,
        ),
    ) -> "SecurityPolicy":
        """Require an external decision for mutating or code-execution actions."""

        gates = [
            PermissionRule(
                identifier=f"security.approval.{capability.value}",
                decision=PolicyDecision.REQUIRE_APPROVAL,
                capability=capability,
                reason="This sensitive action requires human approval.",
            )
            for capability in capabilities
        ]
        return SecurityPolicy([*gates, *self._rules], risk_classifier=self._risk_classifier,
                              risk_decisions=self._risk_decisions)
