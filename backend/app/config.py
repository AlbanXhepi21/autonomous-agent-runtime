"""Central application settings."""

from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _comma_separated(value: str) -> tuple[str, ...]:
    """Split a comma-separated setting, dropping surrounding and empty entries."""

    return tuple(item.strip() for item in value.split(",") if item.strip())


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
    agent_workspace_root: str = "./var"
    max_file_read_bytes: int = Field(default=65_536, ge=1)
    max_file_write_bytes: int = Field(default=65_536, ge=1)
    max_list_files: int = Field(default=100, ge=1)
    command_allowlist: str = "pytest"
    command_timeout_seconds: float = Field(default=15, gt=0)
    max_command_output_bytes: int = Field(default=16_384, ge=1)
    python_exec_timeout_seconds: float = Field(default=10, gt=0)
    max_python_code_bytes: int = Field(default=16_384, ge=1)
    max_python_output_bytes: int = Field(default=16_384, ge=1)
    # A published report embeds rendered charts, so the bound has to admit a
    # document rather than a text file. A single chart PNG already approaches
    # the previous 64KB limit.
    max_artifact_bytes: int = Field(default=10_485_760, ge=1)
    python_exec_allowed_imports: str = "math,statistics,json,datetime,collections"
    summary_trigger_observations: int = Field(default=8, ge=1)
    recent_observations: int = Field(default=5, ge=1)
    database_url: str = Field(default="", repr=False)
    # This is deliberately separate from DATABASE_URL, which belongs to runtime
    # persistence (for example the optional memory backend).
    analytics_database_url: str = Field(default="", repr=False)
    analytics_db_schema: str = "public"
    analytics_schema_cache_ttl_seconds: float = Field(default=300, ge=0)
    analytics_max_result_rows: int = Field(default=5_000, ge=1, le=50_000)
    analytics_max_result_bytes: int = Field(default=1_000_000, ge=1_024)
    analytics_query_timeout_seconds: float = Field(default=15, gt=0, le=120)
    analytics_python_max_dataset_rows: int = Field(default=1_000, ge=1, le=10_000)
    analytics_python_max_dataset_bytes: int = Field(default=500_000, ge=1_024)
    analytics_python_timeout_seconds: float = Field(default=15, gt=0, le=60)
    memory_backend: Literal["in_memory", "postgres"] = "in_memory"
    # `in_memory` keeps artifact records in the process that made them, which is
    # enough for tests and single-process development but loses every download
    # link at restart. `postgres` keeps the record beside the bytes instead.
    artifact_backend: Literal["in_memory", "postgres"] = "in_memory"
    approval_ttl_seconds: int | None = Field(default=3600, ge=1)
    security_environment: Literal["unknown", "development", "staging", "production"] = "unknown"
    analytics_ui_frontend_origins: str = "http://localhost:3000"
    analytics_ui_expose_sql: bool = False
    analytics_ui_max_sql_chars: int = Field(default=4_000, ge=0, le=20_000)
    workbench_developer_mode: bool = False

    # A claim (scheduled_reports.claimed_at, artifacts.deletion_claimed_at)
    # older than this is treated as an abandoned worker, not a live one, and
    # becomes claimable again -- shared by both workers so an operator tunes
    # one number rather than two.
    worker_claim_stale_seconds: int = Field(default=900, ge=1)
    retention_max_deletion_attempts: int = Field(default=5, ge=1)
    # Applied to the artifacts a *scheduled* publish produces; None leaves
    # them with no expiry, matching an ad-hoc manual publish today. This is
    # the one place scheduling and retention are connected by policy rather
    # than by a direct code dependency.
    scheduled_report_artifact_retention_days: int | None = Field(default=90, ge=1)

    # Delivery: webhook has no configuration of its own beyond a per-request
    # destination URL. Email is provider-neutral SMTP, and is only offered by
    # DeliveryService when smtp_host and smtp_from_address are both set --
    # the password itself is resolved through CredentialProvider, never read
    # directly from Settings.
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65_535)
    smtp_username: str = ""
    smtp_from_address: str = ""
    smtp_use_tls: bool = True
    webhook_timeout_seconds: float = Field(default=10, gt=0, le=60)
    #: Only used to build a "secure artifact link" for delivery -- never
    #: exposed to a browser directly, unlike the frontend's own API base URL.
    public_api_base_url: str = "http://localhost:8000"

    @property
    def email_delivery_configured(self) -> bool:
        """Whether enough SMTP configuration exists to attempt email delivery."""

        return bool(self.smtp_host and self.smtp_from_address)

    # Workspace-connected data sources: a workspace's own PostgreSQL, stored
    # encrypted at rest and never the process-wide ANALYTICS_DATABASE_URL.
    #: Resolved through CredentialProvider (reference "datasource_encryption.default"),
    #: never read directly -- kept here only so validate_postgres_configuration
    #: can require it be set at all before any data source can be saved.
    data_source_encryption_key: str = Field(default="", repr=False)
    #: SSRF guard: a connection host resolving to a private/loopback/link-local
    #: address is refused unless this is true. Only for local development.
    datasource_allow_local_hosts: bool = False
    datasource_freshness_stale_after_hours: float = Field(default=48, gt=0)

    @property
    def data_source_encryption_configured(self) -> bool:
        return bool(self.data_source_encryption_key)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def command_allowlist_items(self) -> tuple[str, ...]:
        """Parse the comma-separated allowlist once, here, rather than at each call site."""

        return _comma_separated(self.command_allowlist)

    @property
    def python_exec_allowed_import_items(self) -> tuple[str, ...]:
        """Parse the comma-separated import allowlist once, here."""

        return _comma_separated(self.python_exec_allowed_imports)

    @property
    def frontend_origin_items(self) -> tuple[str, ...]:
        """Parse the comma-separated trusted Workbench origins once, here."""

        return _comma_separated(self.analytics_ui_frontend_origins)

    @model_validator(mode="after")
    def validate_postgres_configuration(self) -> "Settings":
        """Require an explicit URL only when a PostgreSQL backend is selected."""

        if self.memory_backend == "postgres" and not self.database_url:
            raise ValueError("DATABASE_URL is required when MEMORY_BACKEND=postgres")
        if self.artifact_backend == "postgres" and not self.database_url:
            raise ValueError("DATABASE_URL is required when ARTIFACT_BACKEND=postgres")
        return self
