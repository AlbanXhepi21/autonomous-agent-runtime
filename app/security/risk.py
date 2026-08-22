"""Deterministic semantic risk classification for normalized actions."""

from app.security.contracts import (
    Capability, RiskAssessment, RiskCategory, RiskLevel, SecurityAction,
    SecurityEnvironment, SecuritySubject,
)


class RiskClassifier:
    """Classify known runtime capabilities without inspecting model reasoning."""

    def __init__(self, environment: SecurityEnvironment = SecurityEnvironment.UNKNOWN) -> None:
        self._environment = environment

    @property
    def environment(self) -> SecurityEnvironment:
        return self._environment

    def assess(self, subject: SecuritySubject, action: SecurityAction) -> RiskAssessment:
        """Return a conservative rule-based assessment for one normalized action."""

        if action.capability is None:
            return self._assessment(RiskLevel.CRITICAL, RiskCategory.UNKNOWN,
                                    "risk.unknown_action", "Unknown actions are denied by default.")
        if self._is_production_target(action):
            return self._assessment(RiskLevel.CRITICAL, RiskCategory.PRODUCTION_CHANGE,
                                    "risk.production_target", "The action targets a production-like resource.")
        if action.capability in {Capability.CALCULATOR_EVALUATE, Capability.FILESYSTEM_READ,
                                 Capability.REPOSITORY_READ, Capability.WEB_SEARCH,
                                 Capability.DATABASE_SCHEMA_READ}:
            return self._assessment(RiskLevel.LOW, RiskCategory.READ_ONLY,
                                    "risk.read_only", "The action is read-only.")
        if action.capability is Capability.DATABASE_METRIC_READ:
            return self._assessment(RiskLevel.LOW, RiskCategory.READ_ONLY, "risk.metric_read", "Metric definitions are runtime-owned read-only configuration.")
        if action.capability is Capability.DATABASE_QUERY_READ:
            return self._assessment(RiskLevel.MEDIUM, RiskCategory.READ_ONLY,
                                    "risk.database_query", "Read-only database queries can consume shared resources.")
        if action.capability is Capability.ANALYTICS_PYTHON_EXECUTE:
            return self._assessment(RiskLevel.MEDIUM, RiskCategory.CODE_EXECUTION,
                                    "risk.analytics_python", "Restricted analysis runs on a bounded runtime dataset.")
        if action.capability is Capability.ANALYTICS_REPORT_CREATE:
            return self._assessment(RiskLevel.MEDIUM, RiskCategory.LOCAL_MODIFICATION,
                                    "risk.analytics_report", "Report generation creates bounded local artifacts.")
        if action.capability in {Capability.FILESYSTEM_WRITE, Capability.ARTIFACT_CREATE}:
            return self._assessment(RiskLevel.MEDIUM, RiskCategory.LOCAL_MODIFICATION,
                                    "risk.local_modification", "The action modifies local workspace data.")
        if action.capability in {Capability.PYTHON_EXECUTE, Capability.COMMAND_EXECUTE}:
            level = RiskLevel.HIGH if self._environment is SecurityEnvironment.PRODUCTION else RiskLevel.MEDIUM
            return self._assessment(level, RiskCategory.CODE_EXECUTION, "risk.code_execution",
                                    "The action executes controlled local code or a command.")
        if action.capability is Capability.REPOSITORY_WRITE:
            return self._assessment(RiskLevel.HIGH, RiskCategory.DESTRUCTIVE,
                                    "risk.repository_write", "Repository modification is potentially destructive.")
        if action.capability is Capability.AGENT_DELEGATE:
            return self._assessment(RiskLevel.MEDIUM, RiskCategory.EXTERNAL_SIDE_EFFECT,
                                    "risk.delegation", "Delegation creates an additional runtime execution path.")
        return self._assessment(RiskLevel.CRITICAL, RiskCategory.UNKNOWN,
                                "risk.unclassified_capability", "Unclassified capabilities are denied by default.")

    def _is_production_target(self, action: SecurityAction) -> bool:
        identifier = (action.resource.identifier if action.resource else "").lower()
        return self._environment is SecurityEnvironment.PRODUCTION or any(
            marker in identifier for marker in ("production", "prod/", ".prod", "live")
        )

    def _assessment(self, level: RiskLevel, category: RiskCategory, rule_id: str, reason: str) -> RiskAssessment:
        return RiskAssessment(level=level, category=category, reason=reason, rule_id=rule_id,
                              metadata={"environment": self._environment.value})
