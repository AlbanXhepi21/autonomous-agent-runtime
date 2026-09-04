# Repository boundaries

Load this only when a change crosses backend packages, routes, schemas, frontend API code, or generated contracts.

- Start with [backend architecture](../../../../docs/architecture/backend.md) and [development workflow](../../../../docs/contributing/development-workflow.md).
- Keep behavior in its existing owning package. `app/contracts` and `app/core` are leaf packages; do not introduce outward imports.
- For a route, request, or response schema change, follow route → API schema → service → frontend API wrapper/use. Regenerate OpenAPI/types with `cd frontend && npm run gen:api`.
- Run `cd backend && .venv/bin/python -m pytest tests/contracts/test_package_boundaries.py` for backend package-boundary changes.
- Run `cd backend && .venv/bin/python -m pytest tests/contracts/test_openapi_snapshot.py` after API generation when an API contract changed.

Read the authoritative documents above for the detailed package map and boundary exceptions; do not infer a new top-level package from a nearby import.
