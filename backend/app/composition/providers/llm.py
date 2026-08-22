"""The model provider and its pricing table."""

from app.composition.providers.security import get_credential_provider
from app.composition.providers.settings import get_settings
from app.config import Settings
from app.core.logging import register_secret_value
from app.llm.openai_client import OpenAIClient
from app.llm.pricing import PricingRegistry
from app.security import SecretReference


def get_llm_client(settings: Settings | None = None) -> OpenAIClient:
    """Build the configured LLM provider implementation."""

    settings = settings or get_settings()
    api_key = get_credential_provider().resolve(SecretReference(name="openai.default"))
    api_key = api_key or settings.openai_api_key
    if api_key:
        register_secret_value(api_key)
    return OpenAIClient(api_key=api_key, model=settings.openai_model)


def get_pricing_registry() -> PricingRegistry:
    """Return the built-in, versioned model-pricing registry."""

    return PricingRegistry()
