# Prerequisites

Verified against `backend/pyproject.toml`, `frontend/package.json`, and the repository's
companion analytics data generator. Where the repository does not pin a version, this is
stated explicitly rather than guessed.

## Python

- **Required: Python 3.12 or later.**
  Source: `backend/pyproject.toml` — `requires-python = ">=3.12"`. Both `ruff` and `mypy`
  are also configured for `py312`/`3.12` in the same file.

## Node.js

- **No exact minimum version is pinned in the repository** — there is no `.nvmrc`, no
  `.node-version` file, and no `engines` field in `frontend/package.json`.
- In practice, use a current Node.js LTS release compatible with the pinned frontend
  dependencies: `next@16.3.1`, `react@19.2.4`, `typescript@5.9.3`. If you maintain multiple
  Node versions, prefer whichever LTS your Node version manager currently marks active.

## Package managers

- **Backend: `pip`**, inside a virtual environment created with the standard library's
  `venv` module. There is no `requirements.txt`, no Poetry, and no `uv.lock` — all backend
  dependencies are declared in `backend/pyproject.toml` and installed with
  `pip install -e '.[dev]'`.
- **Frontend: `npm`.** `frontend/package-lock.json` is committed and tracked in git;
  no `yarn.lock` or `pnpm-lock.yaml` exists. Use `npm`, not another package manager, so the
  lockfile stays authoritative.

## PostgreSQL

- **Recommended: PostgreSQL 16 or later.**
  The `autonomous-agent` schema itself (see `backend/app/db/records.py`) uses only
  standard column types (UUID, JSONB, timestamps) and generates UUIDs in Python rather than
  with a database-side function or extension, so it does not itself demand a specific
  server version. The **16+ requirement comes from the companion sample-data generator**
  (`../DataGenerator`, referenced from the root `README.md`) that produces the sample
  e-commerce analytics dataset used for the Workbench — its own README states plainly:
  "A standalone, reproducible PostgreSQL 16+ data generator." Run one PostgreSQL 16+ server
  for both the application's own database and the analytics database.
- You will need to create at least one database for the application's own persistence
  (conversations, runs, memory, artifacts, identity, tenancy — depending on which backends
  you enable) and, separately, a database to serve as the read-only analytics source the
  agent investigates. See [Local development](local-development.md).

## Docker

- **Not required, and not provided.** There is no `Dockerfile` or `docker-compose.yml`
  anywhere in this repository (verified: no such files exist under `backend/`, `frontend/`,
  or the repository root). PostgreSQL must be installed and run by some other means —
  a native install, a version manager, or a container you manage yourself. Nothing here
  assumes Docker, and nothing here forbids it either.

## Document-rendering system dependencies

- **None beyond the Python packages installed by `pip install -e '.[dev]'`.**
  - PDF generation uses `reportlab` (pure Python).
  - Word document generation uses `python-docx` (pure Python).
  - Chart rasterization for published documents (`backend/app/analytics/presentation/rasterize.py`)
    draws directly onto `matplotlib.backends.backend_agg.FigureCanvasAgg`, bypassing
    `pyplot` and any interactive/GUI backend entirely — so no display server, X11, or
    system graphics library is required, even in a headless environment.
  - No system fonts, `wkhtmltopdf`, `libreoffice`, or similar external binaries are used
    anywhere in the report pipeline.

## Optional development tools

All are backend/frontend dependencies already declared in the repository, not something
to install separately:

- **`ruff`** (`>=0.6`, backend `[dev]` extra) — linting; configuration in
  `backend/pyproject.toml` (`[tool.ruff]`, line length 120, target `py312`).
- **`mypy`** (`>=1.11`, backend `[dev]` extra) — type checking; configuration in
  `backend/pyproject.toml` (`[tool.mypy]`, target `3.12`).
- **`pytest`** / **`pytest-asyncio`** / **`pypdf`** / **`pypdfium2`** (backend `[dev]`
  extra) — the test suite, including reading generated PDFs back to verify their content
  and rasterizing them to catch layout regressions.
- **`eslint`** and **`prettier`** (frontend `devDependencies`) — linting and formatting.
- **`vitest`** with **`@testing-library/react`** and **`jsdom`** (frontend
  `devDependencies`) — the frontend test runner. There is no end-to-end test tool
  (Playwright/Cypress) in this repository.

## Not needed

- No CI system exists in this repository (no `.github/workflows`, no other CI config
  anywhere), so there is nothing to install to reproduce CI locally — the commands in
  [Local development](local-development.md) and the test commands in this documentation
  are the whole of what a contributor runs.
