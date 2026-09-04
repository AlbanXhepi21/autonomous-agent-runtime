# Environment variables

A quick-lookup reference. For purpose, safe examples, and dev/prod guidance on every
variable, see [getting-started/configuration.md](../getting-started/configuration.md) —
this page exists for fast scanning, not full explanation. All defaults are read directly
from `backend/app/config.py` (`Settings`); no value here is copied from a real `.env`
file.

## Backend (`backend/app/config.py`)

| Variable | Default | Required? | Sensitive? |
|---|---|---|---|
| `OPENAI_API_KEY` | `""` | Needed for any real model call | **Yes** |
| `OPENAI_MODEL` | `"gpt-5.6"` | No | No |
| `LOG_LEVEL` | `INFO` | No | No |
| `LOG_FORMAT` | `pretty` | No | No |
| `MAX_AGENT_ITERATIONS` | 8 | No | No |
| `MAX_AGENT_TOOL_CALLS` | 16 | No | No |
| `MAX_AGENT_RECOVERABLE_ERRORS` | 3 | No | No |
| `MAX_AGENT_CONSECUTIVE_DUPLICATE_ACTIONS` | 2 | No | No |
| `MAX_PARALLEL_SUBAGENTS` | 3 | No | No |
| `MAX_DELEGATIONS_PER_RUN` | 8 | No | No |
| `MAX_SUBAGENT_ITERATIONS` | 6 | No | No |
| `MAX_AGENT_DEPTH` | 1 | No | No |
| `AGENT_WORKSPACE_ROOT` | `./var` | No | No |
| `MAX_FILE_READ_BYTES` | 65536 | No | No |
| `MAX_FILE_WRITE_BYTES` | 65536 | No | No |
| `MAX_LIST_FILES` | 100 | No | No |
| `COMMAND_ALLOWLIST` | `pytest` | No | No |
| `COMMAND_TIMEOUT_SECONDS` | 15 | No | No |
| `MAX_COMMAND_OUTPUT_BYTES` | 16384 | No | No |
| `PYTHON_EXEC_TIMEOUT_SECONDS` | 10 | No | No |
| `MAX_PYTHON_CODE_BYTES` | 16384 | No | No |
| `MAX_PYTHON_OUTPUT_BYTES` | 16384 | No | No |
| `MAX_ARTIFACT_BYTES` | 10485760 | No | No |
| `PYTHON_EXEC_ALLOWED_IMPORTS` | `math,statistics,json,datetime,collections` | No | No |
| `SUMMARY_TRIGGER_OBSERVATIONS` | 8 | No | No |
| `RECENT_OBSERVATIONS` | 5 | No | No |
| `DATABASE_URL` | `""` | **Yes**, for migrations and any `postgres` backend | **Yes** |
| `ANALYTICS_DATABASE_URL` | `""` | Needed for any analysis to run | **Yes** |
| `ANALYTICS_DB_SCHEMA` | `public` | No | No |
| `ANALYTICS_SCHEMA_CACHE_TTL_SECONDS` | 300 | No | No |
| `ANALYTICS_MAX_RESULT_ROWS` | 5000 (max 50000) | No | No |
| `ANALYTICS_MAX_RESULT_BYTES` | 1000000 | No | No |
| `ANALYTICS_QUERY_TIMEOUT_SECONDS` | 15 (max 120) | No | No |
| `ANALYTICS_PYTHON_MAX_DATASET_ROWS` | 1000 (max 10000) | No | No |
| `ANALYTICS_PYTHON_MAX_DATASET_BYTES` | 500000 | No | No |
| `ANALYTICS_PYTHON_TIMEOUT_SECONDS` | 15 (max 60) | No | No |
| `MEMORY_BACKEND` | `in_memory` | No | No |
| `ARTIFACT_BACKEND` | `in_memory` | No | No |
| `APPROVAL_TTL_SECONDS` | 3600 | No | No |
| `SECURITY_ENVIRONMENT` | `unknown` | No — but see [limitations.md](limitations.md) | No |
| `ANALYTICS_UI_FRONTEND_ORIGINS` | `http://localhost:3000` | No | No |
| `ANALYTICS_UI_EXPOSE_SQL` | `false` | No | No |
| `ANALYTICS_UI_MAX_SQL_CHARS` | 4000 (max 20000) | No | No |
| `WORKBENCH_DEVELOPER_MODE` | `false` | No | No |
| `WORKER_CLAIM_STALE_SECONDS` | 900 | No | No |
| `RETENTION_MAX_DELETION_ATTEMPTS` | 5 | No | No |
| `SCHEDULED_REPORT_ARTIFACT_RETENTION_DAYS` | 90 | No | No |
| `SMTP_HOST` | `""` | Only if using email delivery | No |
| `SMTP_PORT` | 587 | No | No |
| `SMTP_USERNAME` | `""` | Only if using email delivery | No |
| `SMTP_FROM_ADDRESS` | `""` | Only if using email delivery | No |
| `SMTP_USE_TLS` | `true` | No | No |
| `SMTP_PASSWORD` | *(not a `Settings` field — see below)* | Only if using email delivery | **Yes** |
| `WEBHOOK_TIMEOUT_SECONDS` | 10 (max 60) | No | No |
| `PUBLIC_API_BASE_URL` | `http://localhost:8000` | No | No |
| `DATA_SOURCE_ENCRYPTION_KEY` | `""` | **Yes**, before any workspace data source can be saved | **Yes** |
| `DATASOURCE_ALLOW_LOCAL_HOSTS` | `false` | No | No |
| `DATASOURCE_FRESHNESS_STALE_AFTER_HOURS` | 48 | No | No |
| `IDENTITY_BACKEND` | `in_memory` | No | No |
| `SESSION_IDLE_TTL_SECONDS` | 43200 | No | No |
| `SESSION_ABSOLUTE_TTL_SECONDS` | 2592000 | No | No |
| `RESET_TOKEN_TTL_SECONDS` | 3600 | No | No |
| `EMAIL_VERIFICATION_TOKEN_TTL_SECONDS` | 259200 | No | No |
| `AUTH_COOKIE_SECURE` | `false` | No — forced true when `SECURITY_ENVIRONMENT=production` | No |
| `APP_BASE_URL` | `http://localhost:3000` | No | No |
| `GITHUB_TOKEN` | *(not a `Settings` field — see below)* | No | **Yes** |
| `TENANCY_BACKEND` | `in_memory` | No | No |
| `INVITATION_TTL_SECONDS` | 604800 | No | No |

## Testing only

| Variable | Purpose |
|---|---|
| `TEST_DATABASE_URL` | Points `postgres`-marked backend tests at a real, migrated database — those tests skip cleanly if unset |

## Frontend (`frontend/.env.local`)

| Variable | Default | Required? | Sensitive? |
|---|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | No | No — `NEXT_PUBLIC_*` values are inlined into the client bundle; never put a secret here |

## The two variables that bypass `.env` entirely

`SMTP_PASSWORD` and `GITHUB_TOKEN` are not `Settings` fields — they're read directly from
the process environment by `EnvironmentCredentialProvider`
(`backend/app/security/credentials.py`) at the moment they're needed, not loaded from
`backend/.env` the way every other variable is. Putting them only in `.env` will not work;
they must be exported as real process/shell environment variables. Full explanation in
[configuration.md](../getting-started/configuration.md#two-variables-that-bypass-env-entirely).
