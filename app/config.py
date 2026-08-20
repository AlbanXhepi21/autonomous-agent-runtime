"""Central application settings."""

from typing import Literal

from pydantic import Field, model_validator
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
    max_parallel_subagents: int = Field(default=3, ge=1)
    max_delegations_per_run: int = Field(default=8, ge=1)
    max_subagent_iterations: int = Field(default=6, ge=1)
    max_agent_depth: int = Field(default=1, ge=0)
    agent_workspace_root: str = "./workspace"
    max_file_read_bytes: int = Field(default=65_536, ge=1)
    max_file_write_bytes: int = Field(default=65_536, ge=1)
    max_list_files: int = Field(default=100, ge=1)
    command_allowlist: str = "pytest"
    command_timeout_seconds: float = Field(default=15, gt=0)
    max_command_output_bytes: int = Field(default=16_384, ge=1)
    python_exec_timeout_seconds: float = Field(default=10, gt=0)
    max_python_code_bytes: int = Field(default=16_384, ge=1)
    max_python_output_bytes: int = Field(default=16_384, ge=1)
    max_artifact_bytes: int = Field(default=65_536, ge=1)
    python_exec_allowed_imports: str = "math,statistics,json,datetime,collections"
    summary_trigger_observations: int = Field(default=8, ge=1)
    recent_observations: int = Field(default=5, ge=1)
    database_url: str = Field(default="", repr=False)
    # This is deliberately separate from DATABASE_URL, which belongs to runtime
    # persistence (for example the optional memory backend).
    analytics_database_url: str = Field(default="", repr=False)
    analytics_db_schema: str = "public"
    analytics_schema_cache_ttl_seconds: float = Field(default=300, ge=0)
    memory_backend: Literal["in_memory", "postgres"] = "in_memory"
    approval_ttl_seconds: int | None = Field(default=3600, ge=1)
    security_environment: Literal["unknown", "development", "staging", "production"] = "unknown"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_postgres_configuration(self) -> "Settings":
        """Require an explicit URL only when PostgreSQL memory is selected."""

        if self.memory_backend == "postgres" and not self.database_url:
            raise ValueError("DATABASE_URL is required when MEMORY_BACKEND=postgres")
        return self
