# Configuration

Every environment variable below is declared in `backend/app/config.py` (the
`Settings` class, loaded via `pydantic-settings` from `backend/.env`), in
`backend/app/security/credentials.py` (two variables resolved directly from the process
environment, not through `Settings` — see the note at the end of this document), or in
`frontend/.env.local` (the one frontend variable). Defaults shown are the code's actual
defaults, not values from any real `.env` file. No secret values are reproduced anywhere
in this document — every "Safe example" below is a placeholder.

**Never commit `.env` or `.env.local` to git.** `.gitignore` excludes `.env*` at the
repository root already.

## Core / LLM

| Name | Purpose | Required? | Safe example | Default | Side | Sensitive? | Dev/prod relevance |
|---|---|---|---|---|---|---|---|
| `OPENAI_API_KEY` | API key for the only configured LLM provider (`app/llm/openai_client.py`) | Optional to boot; needed for any real agent run | `sk-REDACTED` | `""` | Backend | **Sensitive** | Both |
| `OPENAI_MODEL` | Model name passed to the OpenAI client | Optional | `gpt-5.4-mini` | `"gpt-5.6"` in code (`config.py:19`) — note this differs from the `.env.example` value shown above; confirm which your deployment intends | Backend | Non-sensitive | Both |
| `LOG_LEVEL` | Logging verbosity | Optional | `INFO` | `"INFO"` | Backend | Non-sensitive | Both |
| `LOG_FORMAT` | Log output format | Optional | `pretty` | `"pretty"` | Backend | Non-sensitive | Dev (use structured format in prod if you have a log pipeline) |

## Agent runtime limits

| Name | Purpose | Required? | Safe example | Default | Side | Sensitive? | Dev/prod relevance |
|---|---|---|---|---|---|---|---|
| `MAX_AGENT_ITERATIONS` | Ceiling on loop iterations per run | Optional | `8` | `8` | Backend | Non-sensitive | Both |
| `MAX_AGENT_TOOL_CALLS` | Ceiling on tool calls per run | Optional | `16` | `16` | Backend | Non-sensitive | Both |
| `MAX_AGENT_RECOVERABLE_ERRORS` | Ceiling on recoverable errors before a run stops | Optional | `3` | `3` | Backend | Non-sensitive | Both |
| `MAX_AGENT_CONSECUTIVE_DUPLICATE_ACTIONS` | Duplicate-action loop guard | Optional | `2` | `2` | Backend | Non-sensitive | Both |
| `MAX_PARALLEL_SUBAGENTS` | Ceiling on concurrently delegated sub-agents | Optional | `3` | `3` | Backend | Non-sensitive | Both |
| `MAX_DELEGATIONS_PER_RUN` | Ceiling on total delegations per run | Optional | `8` | `8` | Backend | Non-sensitive | Both |
| `MAX_SUBAGENT_ITERATIONS` | Iteration ceiling for a delegated sub-agent | Optional | `6` | `6` | Backend | Non-sensitive | Both |
| `MAX_AGENT_DEPTH` | Maximum delegation nesting depth (`0` disables delegation) | Optional | `1` | `1` | Backend | Non-sensitive | Both |

## Sandboxed execution

| Name | Purpose | Required? | Safe example | Default | Side | Sensitive? | Dev/prod relevance |
|---|---|---|---|---|---|---|---|
| `AGENT_WORKSPACE_ROOT` | Filesystem root the agent's file/command/Python tools are jailed to | Optional | `./var` | `"./var"` | Backend | Non-sensitive | Both |
| `MAX_FILE_READ_BYTES` | Per-file read cap | Optional | `65536` | `65536` | Backend | Non-sensitive | Both |
| `MAX_FILE_WRITE_BYTES` | Per-file write cap | Optional | `65536` | `65536` | Backend | Non-sensitive | Both |
| `MAX_LIST_FILES` | Directory listing cap | Optional | `100` | `100` | Backend | Non-sensitive | Both |
| `COMMAND_ALLOWLIST` | Comma-separated allowlisted executables for `run_command` | Optional | `pytest` | `"pytest"` | Backend | Non-sensitive | **Prod: keep this as narrow as possible** |
| `COMMAND_TIMEOUT_SECONDS` | `run_command` timeout | Optional | `15` | `15` | Backend | Non-sensitive | Both |
| `MAX_COMMAND_OUTPUT_BYTES` | `run_command` output cap | Optional | `16384` | `16384` | Backend | Non-sensitive | Both |
| `PYTHON_EXEC_TIMEOUT_SECONDS` | `python_exec` / `analyze_dataset` timeout | Optional | `10` | `10` | Backend | Non-sensitive | Both |
| `MAX_PYTHON_CODE_BYTES` | Max submitted Python source size | Optional | `16384` | `16384` | Backend | Non-sensitive | Both |
| `MAX_PYTHON_OUTPUT_BYTES` | Max Python execution output size | Optional | `16384` | `16384` | Backend | Non-sensitive | Both |
| `MAX_ARTIFACT_BYTES` | Max size of a registered artifact (e.g. a rendered chart or document) | Optional | `10485760` | `10485760` | Backend | Non-sensitive | Both |
| `PYTHON_EXEC_ALLOWED_IMPORTS` | Comma-separated import allowlist inside the restricted Python sandbox | Optional | `math,statistics,json,datetime,collections` | same | Backend | Non-sensitive | **Prod: keep narrow** — note this default does *not* include `matplotlib`, even though the `analyze_dataset` tool's own description tells the agent to use it for charts; see [Troubleshooting](troubleshooting.md) |
| `SUMMARY_TRIGGER_OBSERVATIONS` | Observation count that triggers context summarization | Optional | `8` | `8` | Backend | Non-sensitive | Both |
| `RECENT_OBSERVATIONS` | Recent-observation window kept unsummarized | Optional | `5` | `5` | Backend | Non-sensitive | Both |

## Persistence backends

| Name | Purpose | Required? | Safe example | Default | Side | Sensitive? | Dev/prod relevance |
|---|---|---|---|---|---|---|---|
| `DATABASE_URL` | Application's own runtime database (conversations, runs, memory, artifacts, identity, tenancy, scheduling, delivery, audit) | **Required to run Alembic migrations at all; required if any `*_BACKEND` below is `postgres`** | `postgresql+asyncpg://user:password@localhost:5432/agent` | `""` | Backend | **Sensitive** (embeds credentials) | Both — in-memory backends are fine for local dev only |
| `MEMORY_BACKEND` | `in_memory` or `postgres` | Optional | `postgres` | `"in_memory"` | Backend | Non-sensitive | **`in_memory` loses all agent memory on restart — use `postgres` outside local dev** |
| `ARTIFACT_BACKEND` | `in_memory` or `postgres` | Optional | `postgres` | `"in_memory"` | Backend | Non-sensitive | **`in_memory` loses artifact records (download links) on restart** |
| `IDENTITY_BACKEND` | `in_memory` or `postgres` | Optional | `postgres` | `"in_memory"` | Backend | Non-sensitive | **`in_memory` loses every account on restart — development/testing only** |
| `TENANCY_BACKEND` | `in_memory` or `postgres` | Optional | `postgres` | `"in_memory"` | Backend | Non-sensitive | Same caveat as above |
| `APPROVAL_TTL_SECONDS` | How long a pending human-approval request stays valid | Optional | `3600` | `3600` | Backend | Non-sensitive | Both |

## Analytics / Workbench

| Name | Purpose | Required? | Safe example | Default | Side | Sensitive? | Dev/prod relevance |
|---|---|---|---|---|---|---|---|
| `ANALYTICS_DATABASE_URL` | Read-only analytics source the agent investigates by default (separate from `DATABASE_URL`) | Optional to boot; **required for any analysis to run** | `postgresql+asyncpg://user:password@localhost:5432/ecommerce_analytics` | `""` | Backend | **Sensitive** (embeds credentials) | Both |
| `ANALYTICS_DB_SCHEMA` | Postgres schema to inspect/query | Optional | `public` | `"public"` | Backend | Non-sensitive | Both |
| `ANALYTICS_SCHEMA_CACHE_TTL_SECONDS` | How long the discovered schema is cached | Optional | `300` | `300` | Backend | Non-sensitive | Both |
| `ANALYTICS_MAX_RESULT_ROWS` | Row cap per query (max `50000`) | Optional | `5000` | `5000` | Backend | Non-sensitive | Both |
| `ANALYTICS_MAX_RESULT_BYTES` | Byte cap per query result | Optional | `1000000` | `1000000` | Backend | Non-sensitive | Both |
| `ANALYTICS_QUERY_TIMEOUT_SECONDS` | Per-query timeout (max `120`) | Optional | `15` | `15` | Backend | Non-sensitive | Both |
| `ANALYTICS_PYTHON_MAX_DATASET_ROWS` | Row cap for `analyze_dataset` (max `10000`) | Optional | `1000` | `1000` | Backend | Non-sensitive | Both |
| `ANALYTICS_PYTHON_MAX_DATASET_BYTES` | Byte cap for `analyze_dataset` | Optional | `500000` | `500000` | Backend | Non-sensitive | Both |
| `ANALYTICS_PYTHON_TIMEOUT_SECONDS` | Timeout for `analyze_dataset` (max `60`) | Optional | `15` | `15` | Backend | Non-sensitive | Both |
| `ANALYTICS_UI_FRONTEND_ORIGINS` | Comma-separated CORS-trusted Workbench origins — **never defaults to a wildcard** | Optional | `http://localhost:3000` | `"http://localhost:3000"` | Backend | Non-sensitive | Update when the frontend origin changes (port, domain) |
| `ANALYTICS_UI_EXPOSE_SQL` | Whether developer traces may include raw SQL | Optional | `false` | `False` | Backend | Non-sensitive | Keep `false` unless actively debugging |
| `ANALYTICS_UI_MAX_SQL_CHARS` | Truncation length for exposed SQL (max `20000`) | Optional | `4000` | `4000` | Backend | Non-sensitive | Both |
| `WORKBENCH_DEVELOPER_MODE` | Enables developer-only endpoints (e.g. the memory inspector) | Optional | `false` | `False` | Backend | Non-sensitive | **Keep `false` in production** |

## Scheduling and retention

| Name | Purpose | Required? | Safe example | Default | Side | Sensitive? | Dev/prod relevance |
|---|---|---|---|---|---|---|---|
| `WORKER_CLAIM_STALE_SECONDS` | How long before an unfinished worker claim (scheduled report or artifact deletion) is treated as abandoned and reclaimable | Optional | `900` | `900` | Backend | Non-sensitive | Both |
| `RETENTION_MAX_DELETION_ATTEMPTS` | Max retries before giving up on deleting an expired artifact's bytes | Optional | `5` | `5` | Backend | Non-sensitive | Both |
| `SCHEDULED_REPORT_ARTIFACT_RETENTION_DAYS` | Retention window applied to artifacts a *scheduled* report produces (`null`/unset = no expiry) | Optional | `90` | `90` | Backend | Non-sensitive | Both |

## Email and webhook delivery

| Name | Purpose | Required? | Safe example | Default | Side | Sensitive? | Dev/prod relevance |
|---|---|---|---|---|---|---|---|
| `SMTP_HOST` | SMTP server host | Optional — email delivery only activates once this and `SMTP_FROM_ADDRESS` are both set | `smtp.example.com` | `""` | Backend | Non-sensitive | Prod only, typically |
| `SMTP_PORT` | SMTP server port | Optional | `587` | `587` | Backend | Non-sensitive | Both |
| `SMTP_USERNAME` | SMTP auth username | Optional | `no-reply@example.com` | `""` | Backend | Non-sensitive (username, not the secret) | Prod only, typically |
| `SMTP_FROM_ADDRESS` | Envelope "from" address | Optional | `no-reply@example.com` | `""` | Backend | Non-sensitive | Prod only, typically |
| `SMTP_USE_TLS` | Whether to use TLS | Optional | `true` | `True` | Backend | Non-sensitive | Both |
| `SMTP_PASSWORD` | SMTP auth password | Optional (with the same activation condition as `SMTP_HOST`) | `REDACTED` | none | Backend | **Sensitive** | **Read directly from the process environment by `EnvironmentCredentialProvider` (`app/security/credentials.py`), not through `Settings`/`.env` — see the note below** |
| `WEBHOOK_TIMEOUT_SECONDS` | Timeout for outbound webhook delivery (max `60`) | Optional | `10` | `10` | Backend | Non-sensitive | Both |
| `PUBLIC_API_BASE_URL` | Base URL used to build artifact links inside delivered emails/webhooks (never sent to a browser) | Optional | `https://api.example.com` | `"http://localhost:8000"` | Backend | Non-sensitive | **Set to your real public URL in prod** |

## Workspace-connected data sources

| Name | Purpose | Required? | Safe example | Default | Side | Sensitive? | Dev/prod relevance |
|---|---|---|---|---|---|---|---|
| `DATA_SOURCE_ENCRYPTION_KEY` | Fernet key encrypting workspace data-source passwords at rest | **Required before any workspace can save a data source connection** | generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` | `""` | Backend | **Sensitive** — rotating it invalidates every stored data source password | Both |
| `DATASOURCE_ALLOW_LOCAL_HOSTS` | Disables the SSRF guard that refuses private/loopback/link-local hosts | Optional | `false` | `False` | Backend | Non-sensitive | **Only ever `true` in local development** |
| `DATASOURCE_FRESHNESS_STALE_AFTER_HOURS` | Hours after which a connected source is flagged stale | Optional | `48` | `48` | Backend | Non-sensitive | Both |

## Identity and sessions

| Name | Purpose | Required? | Safe example | Default | Side | Sensitive? | Dev/prod relevance |
|---|---|---|---|---|---|---|---|
| `SESSION_IDLE_TTL_SECONDS` | Sliding idle session timeout | Optional | `43200` | `43200` | Backend | Non-sensitive | Both |
| `SESSION_ABSOLUTE_TTL_SECONDS` | Hard session cap regardless of activity | Optional | `2592000` | `2592000` | Backend | Non-sensitive | Both |
| `RESET_TOKEN_TTL_SECONDS` | Password-reset token lifetime | Optional | `3600` | `3600` | Backend | Non-sensitive | Both |
| `EMAIL_VERIFICATION_TOKEN_TTL_SECONDS` | Email-verification token lifetime | Optional | `259200` | `259200` | Backend | Non-sensitive | Both |
| `AUTH_COOKIE_SECURE` | Marks auth cookies `Secure` | Optional | `false` | `False` | Backend | Non-sensitive | **Forced `true` automatically when `SECURITY_ENVIRONMENT=production`, regardless of this value** |
| `APP_BASE_URL` | Base URL used inside password-reset/email-verification links | Optional | `http://localhost:3000` | `"http://localhost:3000"` | Backend | Non-sensitive | **Set to your real frontend URL in prod** |
| `SECURITY_ENVIRONMENT` | `unknown` / `development` / `staging` / `production` | Optional | `development` | `"unknown"` | Backend | Non-sensitive | **Set explicitly in every non-local environment** — it also forces cookie security |
| `GITHUB_TOKEN` | Credential for the `github.default` reference used by repository-inspection tooling | Optional | `REDACTED` | none | Backend | **Sensitive** | Same process-environment caveat as `SMTP_PASSWORD` below |

## Tenancy

| Name | Purpose | Required? | Safe example | Default | Side | Sensitive? | Dev/prod relevance |
|---|---|---|---|---|---|---|---|
| `INVITATION_TTL_SECONDS` | Workspace invitation link lifetime | Optional | `604800` | `604800` | Backend | Non-sensitive | Both |

## Testing (not read by the application itself)

| Name | Purpose | Required? | Safe example | Default | Side | Sensitive? | Dev/prod relevance |
|---|---|---|---|---|---|---|---|
| `TEST_DATABASE_URL` | Points the `postgres`-marked backend tests at a real database with migrations already applied | Optional — those tests skip cleanly if unset | `postgresql+asyncpg://user:password@localhost:5432/agent_test` | none | Backend (test-only) | **Sensitive** | Dev/CI only |

## Frontend

| Name | Purpose | Required? | Safe example | Default | Side | Sensitive? | Dev/prod relevance |
|---|---|---|---|---|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Base URL the browser uses to reach the backend API | Optional | `http://localhost:8000` | `"http://localhost:8000"` (client fallback in `src/lib/api/client.ts`) | Frontend | Non-sensitive — `NEXT_PUBLIC_*` variables are inlined into the client bundle, so never put a secret here | **Set to your real public API URL in prod**; developer mode is a *server*-only setting read from `/api/v1/config` — there is no client-side flag for it |

## Two variables that bypass `.env` entirely

`SMTP_PASSWORD` and `GITHUB_TOKEN` are **not** fields on the `Settings` class. They are
resolved at the moment they're needed by `EnvironmentCredentialProvider.resolve()`
(`backend/app/security/credentials.py`), which calls `os.environ.get(...)` directly.
`Settings`' loading of `backend/.env` (via `pydantic-settings`) only populates `Settings`'
own declared fields — it does not call `load_dotenv()` or otherwise inject arbitrary keys
into the process environment (verified: no `load_dotenv` call exists anywhere in the
codebase). **Putting `SMTP_PASSWORD=...` or `GITHUB_TOKEN=...` only in `backend/.env` will
not work** — export them as real environment variables in the shell or process manager
that starts the API, the same way you would any other secret your process manager injects.
