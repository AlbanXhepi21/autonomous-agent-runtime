"""Domain exceptions shared across the application runtime."""


class UnknownToolError(LookupError):
    """Raised when an action names a tool that is not registered."""


class UnknownSkillError(LookupError):
    """Raised when an action names a skill that is not available."""


class SkillMetadataError(ValueError):
    """Raised when a filesystem-defined skill has invalid metadata."""


class UnknownAgentError(LookupError):
    """Raised when a requested specialist agent is not available."""


class AgentDefinitionError(ValueError):
    """Raised when a filesystem-defined specialist agent is invalid."""


class AgentIterationLimitReached(RuntimeError):
    """Reserved for callers that choose to treat a bounded stop as an error."""
