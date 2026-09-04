# Testing map

Load this when selecting, expanding, or explaining validation.

- Start with the nearest backend test file under `backend/tests/unit/`, `api/`, or `integration/`, or the colocated frontend `*.test.ts(x)` file.
- Backend: `cd backend && .venv/bin/python -m pytest tests/path/to/test_file.py`.
- Frontend: `cd frontend && npx vitest run src/path/to/file.test.ts(x)`.
- Run `cd backend && .venv/bin/python -m pytest tests/contracts/` when a structural, security, tenancy, report, or OpenAPI boundary is affected.
- Run `cd backend && ruff check . && mypy app` for changed backend code; run `cd frontend && npm run lint && npm run typecheck && npm test` for changed frontend code when the requested validation scope warrants it.
- Postgres-marked integration tests require migrated `TEST_DATABASE_URL`; report them as unavailable rather than inventing configuration.

For test-support conventions and rendering/evaluation checks, read [testing](../../../../docs/guides/testing.md).
