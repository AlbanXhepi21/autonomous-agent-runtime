# Commands

Every command below exists in the repository as written — none are invented for
convenience. For a guided, ordered walkthrough see
[getting-started/local-development.md](../getting-started/local-development.md); this page
is a flat lookup reference.

## Development

```bash
# Backend dev server (reload enabled)
cd backend && ./scripts/run_api_dev.sh
# equivalent to:
#   python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --reload

# Frontend dev server
cd frontend && npm run dev
```

## Dependency installation

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

# Frontend
cd frontend && npm install
```

## Test commands

```bash
# Backend — database-marked tests skip cleanly if TEST_DATABASE_URL is unset
cd backend && .venv/bin/python -m pytest

# Backend — including database-backed tests (migrations must already be applied)
export TEST_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agent_test
export ANALYTICS_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ecommerce_analytics
.venv/bin/python -m pytest

# Frontend
cd frontend && npm run lint && npm run typecheck && npm test
```

## Linting and type-checking

```bash
# Backend (config in backend/pyproject.toml: [tool.ruff], [tool.mypy])
cd backend && ruff check .
cd backend && mypy app

# Frontend
cd frontend && npm run lint        # eslint .
cd frontend && npm run typecheck   # tsc --noEmit
cd frontend && npm run format      # prettier --write .
```

## Migrations

```bash
cd backend
.venv/bin/python -m alembic upgrade head
```

`DATABASE_URL` must be set — `backend/migrations/env.py` requires it unconditionally, even
if every storage backend is configured as `in_memory`.

## API type generation

```bash
# From frontend/ — dumps the live backend OpenAPI schema, then generates TypeScript types
npm run gen:api
# equivalent to:
#   cd ../backend && .venv/bin/python -m scripts.dump_openapi
#   cd ../frontend && openapi-typescript openapi.json -o src/types/api.generated.ts
```

Requires the backend virtual environment to exist at `backend/.venv` exactly (the script
path is hardcoded relative to `frontend/`).

## Report-preview scripts

```bash
# Render every report template against fixed sample data — PDF, DOCX, and page PNGs —
# for reviewing layout without a live agent run
cd backend && .venv/bin/python -m scripts.preview_reports [output_dir]
# default output: backend/var/.runtime/previews
```

## Documentation commands

```bash
# Regenerate docs/METRICS.md from the live MetricDefinition registry — do not hand-edit the output
cd backend && .venv/bin/python -m scripts.generate_metrics_doc [output_path]
```

## Other operational scripts

```bash
# Rebuild durable artifact records for files written before the artifact store moved to Postgres
cd backend && .venv/bin/python -m scripts.backfill_artifacts [--apply]

# Read-only analytics schema inspection (developer diagnostics)
cd backend && .venv/bin/python -m scripts.inspect_analytics_schema [table_name]

# Sweep expired artifact bytes (see artifacts.md — not started automatically by anything)
cd backend && .venv/bin/python -m scripts.run_artifact_retention [--once] [--interval-seconds N]

# Run due scheduled reports (see reporting.md — not started automatically by anything)
cd backend && .venv/bin/python -m scripts.run_scheduled_reports [--once] [--interval-seconds N]

# Manually exercise predefined scenarios against a running agent API (not part of pytest)
cd backend && .venv/bin/python -m scripts.run_agent_scenarios [--scenario N] [--all] [--output path]

# Deterministic evaluation harness
cd backend && .venv/bin/python -m evals.runner --suite basic|--case ...|--all --json-output report.json
cd backend && .venv/bin/python -m evals.analytics_runner ...
```
