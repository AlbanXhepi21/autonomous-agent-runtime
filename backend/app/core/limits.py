"""Centralized, deterministic runtime limits for an agent run."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeLimits:
    """Hard boundaries enforced by :class:`AgentRunner`."""

    max_iterations: int = 8
    max_tool_calls: int = 16
    max_recoverable_errors: int = 3
    max_consecutive_duplicate_actions: int = 2
    max_parallel_subagents: int = 3
    max_delegations_per_run: int = 8
    max_subagent_iterations: int = 6
    max_agent_depth: int = 1
    #: How many `finish` attempts an investigation plan may redirect before
    #: the runtime accepts a bounded partial completion instead of asking
    #: again. Zero means the first gap is disclosed and accepted immediately.
    max_finish_redirects: int = 2

    def __post_init__(self) -> None:
        for name, value in (
            ("max_iterations", self.max_iterations),
            ("max_tool_calls", self.max_tool_calls),
            ("max_recoverable_errors", self.max_recoverable_errors),
            (
                "max_consecutive_duplicate_actions",
                self.max_consecutive_duplicate_actions,
            ),
            ("max_parallel_subagents", self.max_parallel_subagents),
            ("max_delegations_per_run", self.max_delegations_per_run),
            ("max_subagent_iterations", self.max_subagent_iterations),
            ("max_agent_depth", self.max_agent_depth),
        ):
            if value < 1:
                raise ValueError(f"{name} must be at least 1")
        if self.max_finish_redirects < 0:
            raise ValueError("max_finish_redirects must be at least 0")
