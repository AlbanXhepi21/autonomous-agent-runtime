# Repository instructions

## Work deliberately

- Inspect the relevant code, tests, and local instructions before editing. Search with `rg` before broad file reading.
- Preserve unrelated user changes. Keep the implementation and diff to the smallest scope that satisfies the request; do not refactor unrelated code.
- Run the smallest relevant test first, then the affected contract or broader suite when warranted. Never weaken, delete, or skip tests to make a change pass.
- Inspect the final diff before handoff. Report checks run, generated files changed, and checks not run with their reason.
- Do not expose, log, commit, or invent credentials or other secrets.

## Architecture and security

- Put backend code in its owning package and preserve the import boundaries enforced by `backend/tests/contracts/test_package_boundaries.py`.
- Keep SQL read-only and validated through the SQL AST validator and schema/column allowlists.
- Tenant-owned resources require explicit tenant scope: enforce the workspace boundary in the request path/dependency and in store queries.
- Keep report publishing free of the LLM layer. Renderers consume compiled reports and pre-rasterized images; they must not retrieve run-level facts. Charts carry data only.
- Treat unknown evidence identifiers as unresolved: exclude them from resolved evidence and retain only the existing unresolved/logged diagnostic behavior.
- After any route or request/response-schema change, run `cd frontend && npm run gen:api`; do not edit generated API types by hand.
- Keep migrations hand-written, reversible, and connected to the current Alembic revision chain. Do not use Alembic autogeneration.

## Repository skills

- Use repository-local skills for specialized, multi-step workflows. They keep this file small and load only when relevant.
- `.agents/skills/` is canonical. `.claude/skills/` exposes the same skills to Claude Code; link to canonical content rather than copying it.

## Verified commands

```bash
# Targeted backend test
cd backend && .venv/bin/python -m pytest tests/path/to/test_file.py

# Backend checks
cd backend && .venv/bin/python -m pytest
cd backend && ruff check . && mypy app

# Frontend checks
cd frontend && npm run lint && npm run typecheck && npm test

# API contract generation after a route/schema change
cd frontend && npm run gen:api

# Apply the current application migration chain (requires DATABASE_URL)
cd backend && .venv/bin/python -m alembic upgrade head
```
