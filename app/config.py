"""Central application settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    openai_api_key: str = ""
    openai_model: str = "gpt-5.6"
    log_level: str = "INFO"
    log_format: str = "pretty"
    max_agent_iterations: int = Field(default=8, ge=1)
    max_agent_tool_calls: int = Field(default=16, ge=1)
    max_agent_recoverable_errors: int = Field(default=3, ge=1)
    max_agent_consecutive_duplicate_actions: int = Field(default=2, ge=1)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
