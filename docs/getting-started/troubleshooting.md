# Troubleshooting

Verified fixes for the problems most likely to come up while following
[Local development](local-development.md). Each entry is tied to actual code behavior, not
general advice — file references let you confirm the cause yourself.

## PostgreSQL connection failure

- Confirm the server is actually running and reachable on the host/port in `DATABASE_URL`
  / `ANALYTICS_DATABASE_URL` (`psql "<url-without-the-+asyncpg-part>"` is a quick check
  outside the app).
- Both URLs must use the `postgresql+asyncpg://` scheme — the backend uses `asyncpg`
  exclusively (`backend/pyproject.toml`: `asyncpg>=0.29`); a plain `postgresql://` or
  `postgresql+psycopg://` URL will fail differently (missing driver), not just refuse to
  connect.
- Do not point `DATABASE_URL` and `ANALYTICS_DATABASE_URL` at the same database — they're
  treated as separate concerns throughout the codebase (`app/config.py` comment: "This is
  deliberately separate from DATABASE_URL").

## Missing database migrations

- Symptom, verbatim from the root `README.md`: without applying migrations, "the
  `artifacts` table and the `answer_caveats` column are missing, which makes publishing a
  report fail."
- Fix:
  ```bash
  cd backend
  .venv/bin/python -m alembic upgrade head
  ```
- If this command itself fails with `RuntimeError: DATABASE_URL is required to run Alembic
  migrations`, set `DATABASE_URL` in `backend/.env` first — `backend/migrations/env.py`
  requires it unconditionally, even if you intend to run every backend as `in_memory`.

## Port already in use

- **Backend (`8000`):** `./scripts/run_api_dev.sh` hardcodes `--port 8000`. To use a
  different port, run the underlying command directly instead of the script:
  ```bash
  cd backend
  .venv/bin/python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8001 --reload
  ```
  If you do this, also update `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local` and
  `ANALYTICS_UI_FRONTEND_ORIGINS` in `backend/.env` to match the new port(s) you're using
  end to end.
- **Frontend (`3000`):** Next.js's CLI accepts a port flag:
  ```bash
  npm run dev -- -p 3001
  ```
  If you do this, update `ANALYTICS_UI_FRONTEND_ORIGINS` in `backend/.env` to include the
  new origin (e.g. `http://localhost:3001`) — CORS is origin-exact and never wildcarded
  (`backend/app/main.py`).

## Frontend cannot reach backend

- Check `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local` — the frontend's fetch client
  (`frontend/src/lib/api/client.ts`) falls back to `http://localhost:8000` only if this is
  unset entirely.
- `NEXT_PUBLIC_*` variables are read at dev-server start and inlined at build time —
  **restart `npm run dev`** after changing `frontend/.env.local`; a running dev server will
  not pick up the change.
- Confirm the backend is actually up: `curl -s http://localhost:8000/api/v1/config`.

## CORS or cookie problems

- `ANALYTICS_UI_FRONTEND_ORIGINS` (backend) must list the frontend's exact origin
  (scheme + host + port), comma-separated if more than one. It never defaults to a
  wildcard, by design.
- Auth cookies are set with `samesite="lax"` (`backend/app/api/routes/auth.py`). Browsers
  treat `localhost:3000` and `localhost:8000` as the same site (site = scheme + registrable
  domain, port is not part of it), so this works out of the box for local development —
  **but only if both sides use the same hostname.** If you access the frontend via
  `127.0.0.1:3000` while the API is reached via `localhost:8000` (or vice versa), the
  browser treats them as different sites and will drop the session cookie. Use `localhost`
  consistently on both sides.
- Mutating requests (POST/PATCH/DELETE) must echo the `csrf_token` cookie's value back as
  an `X-CSRF-Token` header — the frontend's API client already does this
  (`frontend/src/lib/api/client.ts`); if you're calling the API directly (`curl`, a
  separate script), you must do the same or you'll get a CSRF rejection.

## Authentication / session problems

- **Registering does not log you in.** `POST /api/v1/auth/register` returns the created
  user with no cookies set; only `POST /api/v1/auth/login` sets the session and CSRF
  cookies (`backend/app/api/routes/auth.py`).
- The session cookie (`session_token`) is `HttpOnly` and never readable from JavaScript;
  the CSRF cookie (`csrf_token`) is deliberately readable so the frontend can copy it into
  a header. If you've cleared cookies for the site, log in again — there is no other
  recovery path.
- `AUTH_COOKIE_SECURE=false` is fine for local `http://localhost` development, but is
  **forced to `true`** whenever `SECURITY_ENVIRONMENT=production`
  (`Settings.effective_cookie_secure`) — a browser will silently refuse to send a `Secure`
  cookie over plain HTTP, which looks like being logged out immediately after logging in.

## Missing model credentials

- `OPENAI_API_KEY` defaults to `""` and is not validated at startup — the API will start
  fine without it. The failure only appears when a run actually reaches its first LLM call.
- Set `OPENAI_API_KEY` in `backend/.env` and restart the API — environment variables are
  read once at process start (`pydantic-settings`), so editing `.env` while the server is
  running has no effect until you restart it.

## Report-rendering dependency errors

- PDF (`reportlab`) and DOCX (`python-docx`) generation, and chart rasterization for
  published documents (`matplotlib`'s `FigureCanvasAgg`, used directly — see
  [Prerequisites](prerequisites.md)), are all pure-Python and installed by
  `pip install -e '.[dev]'`. If report publishing fails, first confirm they're actually
  present in the active virtual environment: `pip show reportlab python-docx matplotlib`.
- Separately: the `analyze_dataset` tool's own description
  (`backend/app/tools/database/analyze.py`) tells the agent to "import matplotlib" to
  produce a chart from restricted Python — but the default
  `PYTHON_EXEC_ALLOWED_IMPORTS=math,statistics,json,datetime,collections` does **not**
  include `matplotlib`, so that specific code path will fail with an import error unless
  you add `matplotlib` to `PYTHON_EXEC_ALLOWED_IMPORTS`. This does not affect the
  dedicated `create_chart` tool, which most Workbench charts use instead.

## Failed API type generation (`npm run gen:api`)

- This script (`frontend/package.json`) runs
  `cd ../backend && .venv/bin/python -m scripts.dump_openapi`, i.e. it hardcodes the
  backend's virtual environment path as `../backend/.venv` relative to `frontend/`. If you
  created the backend virtual environment anywhere else or under a different name, this
  step will fail with a "no such file or directory" error — create it at `backend/.venv`
  exactly as shown in [Local development](local-development.md), or run
  `python -m scripts.dump_openapi` yourself from an activated backend environment and point
  `openapi-typescript` at the resulting file manually.
- This also requires the backend package to actually import cleanly (it calls
  `create_app()` directly, not over HTTP), so run it only after `pip install -e '.[dev]'`
  has succeeded.

## Test database problems

- Backend tests marked `postgres` (`backend/pyproject.toml`: `[tool.pytest.ini_options]`)
  skip automatically and cleanly when `TEST_DATABASE_URL` is unset — a plain
  `pytest` run without it is expected to be green.
- If you do set `TEST_DATABASE_URL`, the suite **never creates its own schema** — apply
  `alembic upgrade head` against that database first, exactly as for the main development
  database, or every `postgres`-marked test will fail outright (not skip) with a
  missing-table error.
- `ANALYTICS_DATABASE_URL` must also be set (and reachable) to run the analytics-dependent
  integration tests — see the exact export commands in
  [Local development](local-development.md#running-the-test-suites).

## Frontend `.env.local.example` file missing after cloning

`frontend/.env.local.example` is matched by the repository's own `.gitignore` pattern
(`.env.*`), and there is no exception carved out for it the way there is for
`backend/.env.example` (which is exempted by name via `!.env.example`). This means a fresh
clone of this repository **does not include `frontend/.env.local.example` at all** —
verified with `git ls-files`, which does not list it. This is a genuine gap in the
repository's own `.gitignore`, not something wrong with your environment.

**Workaround:** create `frontend/.env.local` yourself with:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

This is the file's entire real content (confirmed against a checked-out working copy) —
nothing else is required for local development.
