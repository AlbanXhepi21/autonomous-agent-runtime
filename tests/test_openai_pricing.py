"""OpenAI model-specific token pricing coverage."""

from decimal import Decimal

import pytest

from app.llm.base import LLMUsage
from app.llm.pricing import (
    InvalidTokenUsageError,
    OPENAI_MODEL_PRICES,
    UnsupportedOpenAIModelError,
    calculate_openai_cost,
    normalize_openai_model,
)


@pytest.mark.parametrize("model", [*OPENAI_MODEL_PRICES, "gpt-5.6"])
def test_every_supported_model_has_decimal_pricing(model: str) -> None:
    assert isinstance(calculate_openai_cost(model, 1_000_000, 0, 0), Decimal)


def test_alias_and_snapshot_names_normalize_exactly() -> None:
    assert normalize_openai_model("gpt-5.6") == "gpt-5.6-sol"
    assert normalize_openai_model("gpt-5.4-mini-2026-03-17") == "gpt-5.4-mini"
    with pytest.raises(UnsupportedOpenAIModelError, match="totally-unrelated"):
        normalize_openai_model("totally-unrelated-2026-03-17")


def test_cost_mixes_uncached_cached_and_output_with_decimal_precision() -> None:
    cost = calculate_openai_cost("gpt-5.4-mini", 1_000_000, 200_000, 100_000)
    assert cost == Decimal("1.065")
    assert calculate_openai_cost("gpt-5.4-pro", 100, 100, 0) == Decimal("0.003")
    assert calculate_openai_cost("gpt-5.4-nano", 0, 0, 0) == Decimal("0")


@pytest.mark.parametrize("kwargs", [
    {"input_tokens": -1},
    {"input_tokens": 1, "cached_input_tokens": 2},
])
def test_invalid_token_accounting_is_rejected(kwargs: dict[str, int]) -> None:
    with pytest.raises(InvalidTokenUsageError):
        calculate_openai_cost("gpt-5.4", output_tokens=0, **kwargs)


def test_long_context_boundary_and_uplift() -> None:
    at_threshold = calculate_openai_cost("gpt-5.5", 272_000, 0, 100)
    above_threshold = calculate_openai_cost("gpt-5.5", 272_001, 0, 100)
    assert at_threshold == Decimal("1.363")
    assert above_threshold == Decimal("2.724510")
    # Mini is intentionally not eligible for the long-context uplift.
    assert calculate_openai_cost("gpt-5.4-mini", 272_001, 0, 0) == Decimal("0.20400075")


def test_cache_write_is_only_charged_when_explicitly_provided() -> None:
    assert calculate_openai_cost("gpt-5.6", 0, 0, 0, 10) == Decimal("0.0000625")
    usage = LLMUsage(input_tokens=100, output_tokens=1)
    assert usage.cache_write_tokens is None
