# API synchronization

Load this only for routes, API schemas, OpenAPI, generated frontend types, API wrappers, or SSE contracts.

- API schemas live in `backend/app/api/schemas/`; request models use `ConfigDict(extra="forbid")`.
- Follow the existing route's error shape. The API has structured and string `detail` variants, so do not normalize responses opportunistically.
- Run the closest backend API test, then `cd frontend && npm run gen:api`. That command runs `cd ../backend && .venv/bin/python -m scripts.dump_openapi` and `openapi-typescript openapi.json -o src/types/api.generated.ts`.
- Run `cd backend && .venv/bin/python -m pytest tests/contracts/test_openapi_snapshot.py`, then targeted frontend tests and `cd frontend && npm run typecheck`.
- Keep `frontend/src/types/api.generated.ts` generated; place any necessary hand-written aliases in the existing `frontend/src/types/api.ts` pattern.

For endpoint and SSE conventions, read [API overview](../../../../docs/api/overview.md) and [streaming events](../../../../docs/api/streaming-events.md).
