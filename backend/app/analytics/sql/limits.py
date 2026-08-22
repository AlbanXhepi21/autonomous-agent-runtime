"""Immutable limits for one analytics SQL execution."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalyticsQueryLimits:
    max_result_rows: int = 5_000
    max_result_bytes: int = 1_000_000
    timeout_seconds: float = 15

    def __post_init__(self) -> None:
        if self.max_result_rows < 1 or self.max_result_bytes < 1 or self.timeout_seconds <= 0:
            raise ValueError("Analytics query limits must be positive.")
