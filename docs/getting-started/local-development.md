# Local development

An exact, verified setup sequence for running `autonomous-agent` locally: backend API,
frontend Workbench, and the PostgreSQL databases both depend on. Every command below
exists in the repository as written (a script, an `npm`/`pip` entry point, or a documented
CLI) — none are invented for convenience. See [Configuration](configuration.md) for what
every environment variable does, and [Troubleshooting](troubleshooting.md) if a step here
doesn't behave as described.

## 1. Clone and enter the repository

```bash
git clone <your-repository-url> autonomous-agent
cd autonomous-agent
```

## 2. Install backend dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e '.[dev]'
```

This installs the runtime dependencies (FastAPI, SQLAlchemy, Alembic, sqlglot, OpenAI's
SDK, reportlab, python-docx, matplotlib, etc.) and the `[dev]` extras (`pytest`, `ruff`,
`mypy`, `pypdf`, `pypdfium2`).

## 3. Install frontend dependencies

```bash
cd ../frontend
npm install
```

## 4. Create local configuration

Backend:

```bash
cd ../backend
cp .env.example .env
```

Then edit `backend/.env` and set, at minimum, `OPENAI_API_KEY` (required for the agent to
make any real model call) and `DATABASE_URL` (required to run migrations in step 6 — see
[Configuration](configuration.md)).

Frontend:

```bash
cd ../frontend
cp .env.local.example .env.local
```

**If this file is missing after cloning**, see the note in
[Troubleshooting](troubleshooting.md#frontend-envlocalexample-file-missing-after-cloning) —
`.env.local.example` is currently excluded by the repository's `.gitignore` pattern and may
not exist in a fresh clone. If so, create `frontend/.env.local` by hand with a single line:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## 5. Start required services

`autonomous-agent` does not run or manage PostgreSQL for you — there is no Docker Compose
file in this repository. Start a PostgreSQL 16+ server by whatever means you normally use
(a native install, a version manager, or your own container), then create two databases:
one for the application's own runtime persistence, and one to act as the analytics source
the agent investigates:

```bash
createdb agent
createdb ecommerce_analytics
```

Point `backend/.env` at them:

```env
DATABASE_URL=postgresql+asyncpg://<user>:<password>@localhost:5432/agent
ANALYTICS_DATABASE_URL=postgresql+asyncpg://<user>:<password>@localhost:5432/ecommerce_analytics
```

Do not reuse the same database for both — `ANALYTICS_DATABASE_URL` is treated as an
external, read-only source and is queried with different assumptions than the
application's own tables.

## 6. Apply Alembic migrations

```bash
cd backend
.venv/bin/python -m alembic upgrade head
```

`DATABASE_URL` must be set before running this — `backend/migrations/env.py` raises
`RuntimeError("DATABASE_URL is required to run Alembic migrations")` otherwise, regardless
of which storage backend (`in_memory` or `postgres`) you plan to select for
`MEMORY_BACKEND`, `ARTIFACT_BACKEND`, `IDENTITY_BACKEND`, or `TENANCY_BACKEND`. Tables are
never created at process startup — skipping this step is the single most common way to get
a broken local environment (see [Troubleshooting](troubleshooting.md)).

## 7. Initialize or seed the analytics database

`autonomous-agent` does not include its own seed data or seed script for
`ANALYTICS_DATABASE_URL` — it is designed to investigate whatever real analytics database
you point it at, discovering the schema at runtime. The repository's own `README.md`
references a companion, separately maintained project for generating a realistic sample
dataset:

```bash
# from alongside (not inside) this repository, if you have it available:
cd ../DataGenerator
cp .env.example .env       # set DATABASE_URL to your ecommerce_analytics database
python3.12 -m pip install -r requirements.txt
python generate.py --scale small --drop-existing
```

That project's own `README.md` documents its requirements (PostgreSQL 16+) and generation
profiles (`small`, `medium`, `large`) in full; treat it as a separate, external tool, not
part of this repository.

If you don't have that project available, point `ANALYTICS_DATABASE_URL` at any existing
PostgreSQL database you have read access to — the agent's schema-discovery tools
(`list_tables`, `describe_table`, `search_schema`) work against arbitrary schemas, not a
hardcoded one.

## 8. Start FastAPI

```bash
cd backend
./scripts/run_api_dev.sh
```

This script checks that backend dependencies are actually importable (exits with a clear
message telling you to re-run `pip install -e '.[dev]'` if not), then runs:

```bash
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --reload
```

The API is available at `http://localhost:8000`, with interactive OpenAPI docs at
`http://localhost:8000/docs`.

## 9. Start Next.js

In a separate terminal:

```bash
cd frontend
npm run dev
```

The Workbench is available at `http://localhost:3000`.

## 10. Verify health endpoints

There is no dedicated `/health` route in this API. Use these instead:

- **Backend, no login required:**
  ```bash
  curl -s http://localhost:8000/api/v1/config
  ```
  Expect a JSON body like `{"developer_mode":false}`.
- **Backend interactive docs:** open `http://localhost:8000/docs` in a browser — the
  Swagger UI should load and list all routers.
- **Frontend:** open `http://localhost:3000/login` — this route renders without
  authentication; if it loads, the Next.js dev server and its build are healthy.

## 11. Run a first analysis

1. Open `http://localhost:3000/register` and create an account.
2. Log in at `http://localhost:3000/login`. (Registering does not log you in automatically
   — these are two separate steps, confirmed in `backend/app/api/routes/auth.py`: only
   `login` sets the session/CSRF cookies.)
3. A brand-new account has no workspace yet, so you land on an onboarding screen — create
   your first workspace/organization there.
4. You're redirected into the Workbench at `/w/<workspaceId>`.
5. Type a question into the chat composer, for example:
   ```text
   What is total revenue?
   ```
   Submitting this calls `POST /api/v1/workspaces/<workspaceId>/analytics/runs` and streams
   progress over Server-Sent Events as the agent investigates.

If no active data source is configured for the workspace, the run falls back to the
built-in demo analytics database (`ANALYTICS_DATABASE_URL`) — see
`backend/app/api/routes/agent.py` and [`../DATASOURCES.md`](../DATASOURCES.md) if you
want to connect a workspace-specific PostgreSQL source instead. If `ANALYTICS_DATABASE_URL`
is unset or unreachable, this step will fail — see [Troubleshooting](troubleshooting.md).

## 12. Stop local services safely

- **Backend:** `Ctrl+C` in the terminal running `run_api_dev.sh`. Uvicorn's reloader and
  worker process both shut down on the interrupt.
- **Frontend:** `Ctrl+C` in the terminal running `npm run dev`.
- **PostgreSQL:** however you started it — this repository does not manage its lifecycle.
  For example, `brew services stop postgresql@16` (Homebrew on macOS),
  `sudo systemctl stop postgresql` (systemd on Linux), or `docker stop <container>` if you
  chose to run Postgres in a container yourself.

## Running the test suites

Not part of first setup, but verified and worth knowing once the environment above works:

```bash
cd backend && .venv/bin/python -m pytest          # database-dependent tests skip cleanly
```

```bash
cd frontend && npm run lint && npm run typecheck && npm test
```

See [Configuration](configuration.md) for `TEST_DATABASE_URL` and the other variables the
database-backed backend tests require.
