"""Versioned OpenAI model pricing and deterministic USD cost calculation."""

import re
from dataclasses import dataclass
from decimal import Decimal

from app.llm.contracts import LLMUsage

MILLION_TOKENS = Decimal("1000000")
LONG_CONTEXT_INPUT_THRESHOLD = 272_000
LONG_CONTEXT_INPUT_MULTIPLIER = Decimal("2")
LONG_CONTEXT_OUTPUT_MULTIPLIER = Decimal("1.5")


class UnsupportedOpenAIModelError(ValueError):
    """Raised when a model name cannot be mapped to a documented price."""


class InvalidTokenUsageError(ValueError):
    """Raised when reported token accounting is internally inconsistent."""


def _decimal(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """USD prices per one million tokens for one OpenAI model family."""

    input_per_million: Decimal | int | float | str
    output_per_million: Decimal | int | float | str
    cached_input_per_million: Decimal | int | float | str | None = None
    cache_write_per_million: Decimal | int | float | str | None = None
    long_context_pricing: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_per_million", _decimal(self.input_per_million))
        object.__setattr__(self, "output_per_million", _decimal(self.output_per_million))
        if self.cached_input_per_million is not None:
            object.__setattr__(self, "cached_input_per_million", _decimal(self.cached_input_per_million))
        if self.cache_write_per_million is not None:
            object.__setattr__(self, "cache_write_per_million", _decimal(self.cache_write_per_million))

    @property
    def input(self) -> Decimal:
        return self.input_per_million

    @property
    def cached_input(self) -> Decimal | None:
        return self.cached_input_per_million

    @property
    def output(self) -> Decimal:
        return self.output_per_million


# `gpt-5.6` is deliberately resolved to `gpt-5.6-sol`.
OPENAI_MODEL_PRICES: dict[str, ModelPricing] = {
    "gpt-5.4": ModelPricing("2.50", "15.00", "0.25", long_context_pricing=True),
    "gpt-5.4-pro": ModelPricing("30.00", "180.00", "30.00", long_context_pricing=True),
    "gpt-5.4-mini": ModelPricing("0.75", "4.50", "0.075"),
    "gpt-5.4-nano": ModelPricing("0.20", "1.25", "0.02"),
    "gpt-5.5": ModelPricing("5.00", "30.00", "0.50", long_context_pricing=True),
    "gpt-5.5-pro": ModelPricing("30.00", "180.00", "30.00", long_context_pricing=True),
    "gpt-5.6-sol": ModelPricing("5.00", "30.00", "0.50", "6.25", long_context_pricing=True),
    "gpt-5.6-terra": ModelPricing("2.00", "12.00", "0.20", "2.50", long_context_pricing=True),
    "gpt-5.6-luna": ModelPricing("0.20", "1.20", "0.02", "0.25", long_context_pricing=True),
}
_SNAPSHOT_SUFFIX = re.compile(r"^(.+)-(\d{4}-\d{2}-\d{2})$")


def normalize_openai_model(model: str) -> str:
    """Return an exact supported pricing model for an alias or dated snapshot."""

    candidate = model.strip()
    if candidate == "gpt-5.6":
        return "gpt-5.6-sol"
    if candidate in OPENAI_MODEL_PRICES:
        return candidate
    snapshot = _SNAPSHOT_SUFFIX.fullmatch(candidate)
    if snapshot and snapshot.group(1) in OPENAI_MODEL_PRICES:
        return snapshot.group(1)
    supported = ", ".join([*OPENAI_MODEL_PRICES, "gpt-5.6"])
    raise UnsupportedOpenAIModelError(
        f"Unsupported OpenAI model {model!r} for cost calculation. Supported models: {supported}."
    )


def calculate_openai_cost(
    model: str,
    input_tokens: int,
    cached_input_tokens: int = 0,
    output_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> Decimal:
    """Calculate one documented OpenAI request cost in exact USD decimals."""

    if any(value < 0 for value in (input_tokens, cached_input_tokens, output_tokens, cache_write_tokens)):
        raise InvalidTokenUsageError("OpenAI token counts cannot be negative.")
    if cached_input_tokens > input_tokens:
        raise InvalidTokenUsageError("Cached input tokens cannot exceed total input tokens.")
    pricing = OPENAI_MODEL_PRICES[normalize_openai_model(model)]
    if cached_input_tokens and pricing.cached_input_per_million is None:
        raise InvalidTokenUsageError(f"{model!r} does not define cached-input pricing.")
    if cache_write_tokens and pricing.cache_write_per_million is None:
        raise InvalidTokenUsageError(f"{model!r} does not define cache-write pricing.")
    input_multiplier = LONG_CONTEXT_INPUT_MULTIPLIER if (
        pricing.long_context_pricing and input_tokens > LONG_CONTEXT_INPUT_THRESHOLD
    ) else Decimal("1")
    output_multiplier = LONG_CONTEXT_OUTPUT_MULTIPLIER if input_multiplier != 1 else Decimal("1")
    uncached_input_tokens = input_tokens - cached_input_tokens
    return (
        Decimal(uncached_input_tokens) * pricing.input_per_million * input_multiplier
        + Decimal(cached_input_tokens) * (pricing.cached_input_per_million or Decimal("0")) * input_multiplier
        + Decimal(output_tokens) * pricing.output_per_million * output_multiplier
        # Cache writes are charged only when a provider explicitly reports them.
        + Decimal(cache_write_tokens) * (pricing.cache_write_per_million or Decimal("0")) * input_multiplier
    ) / MILLION_TOKENS


class PricingRegistry:
    """Versioned OpenAI pricing plus optional custom test/integration prices."""

    version = "2026-08-21"

    def __init__(self, prices: dict[str, ModelPricing] | None = None) -> None:
        self._prices = {**OPENAI_MODEL_PRICES, **(prices or {})}

    def get(self, model: str | None) -> ModelPricing | None:
        if not model:
            return None
        try:
            return self._prices.get(normalize_openai_model(model))
        except UnsupportedOpenAIModelError:
            return self._prices.get(model)


def estimate_cost(usage: LLMUsage | None, pricing: ModelPricing | None, *, model: str | None = None) -> float | None:
    """Compatibility wrapper; all built-in OpenAI calculation is centralized above."""

    if usage is None or pricing is None or usage.input_tokens is None or usage.output_tokens is None:
        return None
    cached = usage.cached_input_tokens or 0
    cache_write = usage.cache_write_tokens or 0
    if cached and pricing.cached_input_per_million is None:
        return None
    if cache_write and pricing.cache_write_per_million is None:
        return None
    if model is not None:
        try:
            return float(calculate_openai_cost(model, usage.input_tokens, cached, usage.output_tokens, cache_write))
        except InvalidTokenUsageError:
            return None
        except UnsupportedOpenAIModelError:
            # A caller may provide a non-OpenAI integration price in its own
            # registry. It still uses the same arithmetic, without model rules.
            pass
    uncached = usage.input_tokens - cached
    if uncached < 0:
        return None
    return float((Decimal(uncached) * pricing.input_per_million
                  + Decimal(cached) * (pricing.cached_input_per_million or Decimal("0"))
                  + Decimal(usage.output_tokens) * pricing.output_per_million
                  + Decimal(cache_write) * (pricing.cache_write_per_million or Decimal("0"))) / MILLION_TOKENS)
