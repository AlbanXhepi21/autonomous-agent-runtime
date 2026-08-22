"""Runtime configuration."""

from app.composition.lifecycle import provider
from app.config import Settings


@provider
def get_settings() -> Settings:
    """Return the shared settings instance."""

    return Settings()
