# Testing

## Backend tests

```bash
cd backend && .venv/bin/python -m pytest
```

Organized under `backend/tests/`: `api/` (14 files, HTTP-surface tests — each spins up a
standalone `FastAPI()` app with only the relevant router and an in-memory service, no
database), `contracts/` (9 files, structural rules — see below), `fixtures/` (shared test
data, e.g. a hand-built completed-investigation fixture), `integration/` (26 files, mostly
`postgres`-marked), `unit/` (~85 files, one subtree per backend package).

Shared test infrastructure lives in `backend/tests/support.py` (exposed as fixtures via
`backend/tests/conftest.py`):
- `ScriptedLLM` — an `LLMClient` implementation that replays a fixed `AgentAction` (or
  list of them) instead of calling a real model, repeating the last one once exhausted.
- `make_runner(llm, tool_registry=None, skill_registry=None, **overrides)` — builds an
  `AgentRunner` with empty registries by default.
- `make_tenant_context(...)` / `override_tenant_context(app, ...)` — build or inject a
  self-consistent fake tenant context, bypassing real auth/CSRF for API-layer tests that
  aren't testing auth itself.
- `logged_event(records, event)` — finds one structured log event by message in captured
  log records, with a clear failure message instead of a bare `StopIteration`.

There is no dedicated test harness *class* beyond these functions — most tests construct
what they need inline (e.g. a `ToolRegistry()` + `ToolExecutor(registry)` per test).

## Frontend tests

```bash
cd frontend && npm test          # vitest run
cd frontend && npm run lint      # eslint .
cd frontend && npm run typecheck # tsc --noEmit
```

47 test files, all colocated next to their source under `src/`, using Vitest +
`@testing-library/react` + `jsdom`. No end-to-end browser test tool exists in this
repository (no Playwright/Cypress) — component/unit coverage plus the backend's OpenAPI
snapshot test are what stand in for cross-stack integration coverage.

## Integration tests

Marked `postgres` (`backend/pyproject.toml`: `[tool.pytest.ini_options] markers`) and
**skip cleanly** when the relevant database URL is unset — a plain `pytest` run is
expected to be fully green without a database. To run them:

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agent_test
export ANALYTICS_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ecommerce_analytics
cd backend && .venv/bin/python -m alembic upgrade head   # against TEST_DATABASE_URL
.venv/bin/python -m pytest
```

The skip guard pattern (`backend/tests/integration/test_postgres_artifacts.py` and every
other file in this directory):

```python
pytestmark = pytest.mark.postgres
...
if not TEST_DATABASE_URL:
    pytest.skip("TEST_DATABASE_URL is not configured")
```

These tests **never create their own schema** — migrations must already be applied to
whichever database `TEST_DATABASE_URL` points at.

## Migration tests

There is no separate migration test suite — see
[database-migrations.md](database-migrations.md#testing-a-migration). Confidence in a
migration comes from successfully running `alembic upgrade head` against a fresh database
and then passing the full `postgres`-marked integration suite against it.

## Package-boundary tests

`backend/tests/contracts/test_package_boundaries.py` parses the AST import graph of every
file under `backend/app/` and asserts, without exception: no import cycle exists between
any two top-level packages, and `contracts`/`core` (the two leaf packages) import nothing
outside each other. See [backend.md](../architecture/backend.md#package-boundaries) for
the one known stale check inside this file (it still names a package, `app.agent`, that no
longer exists). Other structural contract tests worth knowing about:
`test_datasource_boundaries.py`, `test_identity_boundaries.py`,
`test_tenancy_boundaries.py`, `test_report_boundaries.py`,
`test_saved_report_boundaries.py`, `test_scheduling_delivery_boundaries.py`,
`test_public_event_contract.py`.

## OpenAPI snapshot

`backend/tests/contracts/test_openapi_snapshot.py` regenerates the live app's OpenAPI
schema in-process (`create_app().openapi()`), normalizes it (`json.dumps(...,
sort_keys=True)` then reparsed — a semantic comparison, not byte-for-byte), and asserts it
equals the committed `frontend/openapi.json`. Forgetting to regenerate after an API change
fails the suite with: *"The API schema changed but frontend/openapi.json was not
regenerated. Run `npm run gen:api` from frontend/ and commit the result."* See
[api/overview.md](../api/overview.md#openapi-and-type-generation).

## Document rendering verification

Generated PDFs and DOCX files are verified by **reading them back**, never by comparing
raw bytes (which would only prove determinism, not correctness): PDF text via `pypdf`,
DOCX structure via `python-docx` (both backend `[dev]` extras). Layout regressions that a
text-only assertion can't catch (a stranded heading, a collapsed table) are caught instead
by rendering every template to page images against fixed sample data:

```bash
cd backend && .venv/bin/python -m scripts.preview_reports [output_dir]
```

`pypdfium2` (also a `[dev]` extra) does the PDF-to-image rasterization for this script.

## Evaluation harness

A custom, deterministic harness — not a third-party framework, not wired into any CI
(there is none in this repository):

```bash
cd backend && .venv/bin/python -m evals.runner --suite basic --json-output report.json
cd backend && .venv/bin/python -m evals.analytics_runner ...
```

Uses a `ScriptedEvalLLM` that replays a fixed action sequence — no live model calls, fully
deterministic. Datasets live in `backend/evals/datasets/` (`basic.json`,
`analytics_cases.json` — 26 cases, plus smaller sets for delegation, environment, memory,
reliability, security, skills, tools).

## Linting and type checking

```bash
cd backend && ruff check .      # line-length 120, target py312
cd backend && mypy app
cd frontend && npm run lint     # eslint-config-next
cd frontend && npm run typecheck # tsc --noEmit, strict mode
```

No CI runs any of this automatically — see
[operations/production-checklist.md](../operations/production-checklist.md).

## Targeted test examples

```bash
# One backend file
cd backend && .venv/bin/python -m pytest tests/unit/tools/test_tools.py

# One test by name
cd backend && .venv/bin/python -m pytest tests/unit/analytics/test_analytics_sql.py -k rejects_mutating

# Just the package-boundary and OpenAPI contract tests
cd backend && .venv/bin/python -m pytest tests/contracts/

# One frontend file
cd frontend && npx vitest run src/lib/tenancy/resolve.test.ts
```

## Required external services

| Test tier | Requires |
|---|---|
| Backend unit + API tests | Nothing — fully in-memory/mocked |
| Backend `postgres`-marked integration tests | A real PostgreSQL database, migrated, referenced by `TEST_DATABASE_URL` |
| Metric-rerun arithmetic tests specifically | Additionally, `ANALYTICS_DATABASE_URL` pointed at a database with the demo e-commerce schema populated (see [local-development.md](../getting-started/local-development.md)) |
| Frontend tests | Nothing — jsdom, no real browser or backend |
| `scripts.preview_reports` | Nothing — renders from fixed, hardcoded sample data |
| Evaluation harness | Nothing — the harness's own `ScriptedEvalLLM` never calls OpenAI |

No test tier in this repository requires a real OpenAI API key.
