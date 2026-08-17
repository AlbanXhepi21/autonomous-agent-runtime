"""Centralized, deterministic runtime limits for an agent run."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeLimits:
    """Hard boundaries enforced by :class:`AgentRunner`."""

    max_iterations: int = 8
    max_tool_calls: int = 16
    max_recoverable_errors: int = 3
    max_consecutive_duplicate_actions: int = 2

    def __post_init__(self) -> None:
        for name, value in (
            ("max_iterations", self.max_iterations),
            ("max_tool_calls", self.max_tool_calls),
            ("max_recoverable_errors", self.max_recoverable_errors),
            (
                "max_consecutive_duplicate_actions",
                self.max_consecutive_duplicate_actions,
            ),
        ):
            if value < 1:
                raise ValueError(f"{name} must be at least 1")
