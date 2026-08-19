"""Explicitly versioned pricing inputs and deterministic cost calculation."""

from dataclasses import dataclass

from app.llm.base import LLMUsage


@dataclass(frozen=True, slots=True)
class ModelPricing:
    input_per_million: float
    output_per_million: float
    cached_input_per_million: float | None = None


class PricingRegistry:
    """Runtime-configurable pricing registry; an empty registry means unknown cost."""

    version = "2026-08-19"

    def __init__(self, prices: dict[str, ModelPricing] | None = None) -> None:
        self._prices = dict(prices or {})

    def get(self, model: str | None) -> ModelPricing | None:
        return self._prices.get(model) if model else None


def estimate_cost(usage: LLMUsage | None, pricing: ModelPricing | None) -> float | None:
    """Return null when usage or configured pricing cannot support a real estimate."""

    if usage is None or pricing is None or usage.input_tokens is None or usage.output_tokens is None:
        return None
    cached = usage.cached_input_tokens or 0
    if cached and pricing.cached_input_per_million is None:
        return None
    uncached_input = max(usage.input_tokens - cached, 0)
    return ((uncached_input * pricing.input_per_million) + (usage.output_tokens * pricing.output_per_million)
            + (cached * (pricing.cached_input_per_million or 0))) / 1_000_000
