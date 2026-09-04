# Pull requests

This repository has **no CI** — every check below is currently a manual step for the
author and reviewer, not something a merge button will refuse to allow if skipped. Treat
this checklist as replacing the automation that doesn't exist yet, not as optional extra
diligence.

## Before opening

- [ ] `cd backend && .venv/bin/python -m pytest` passes (database-marked tests skip
      cleanly without a database — that's expected, not a failure)
- [ ] If the change touches anything database-backed, also run the `postgres`-marked
      suite against a real, migrated database (see [testing.md](../guides/testing.md))
- [ ] `cd backend && ruff check . && mypy app` passes
- [ ] `cd frontend && npm run lint && npm run typecheck && npm test` passes
- [ ] If any route, request schema, or response schema changed:
      `cd frontend && npm run gen:api`, and `frontend/openapi.json` is included in the
      diff (`test_openapi_snapshot.py` will otherwise fail for anyone who pulls this
      change)
- [ ] If `backend/app/analytics/semantics/metrics.py` changed:
      `cd backend && .venv/bin/python -m scripts.generate_metrics_doc`, and
      `docs/METRICS.md` is included in the diff
- [ ] If a new migration was added: it has a real `downgrade()`, and `alembic upgrade
      head` succeeds against a fresh database

## Description

Since there's no PR template in this repository, at minimum state:
- What changed and why (the "why" matters more here — see
  [coding-conventions.md](coding-conventions.md)'s docstring-rationale convention; a PR
  description should carry the same kind of "why," not just restate the diff).
- Which package boundaries the change touches, if any — call out explicitly if you added
  a new top-level `app/` package or changed what one is allowed to import.
- Whether the change affects a tool/skill/specialist/metric/chart type/report template's
  public shape — if so, link to the relevant developer guide
  (e.g. [adding-a-tool.md](../guides/adding-a-tool.md)) to show the required steps were
  followed (capability mapping, tests, documentation).

## Review checklist

A reviewer should verify, since nothing else will:

- [ ] Package-boundary test (`test_package_boundaries.py`) wasn't worked around by an
      import that shouldn't exist
- [ ] A new tool has a `_TOOL_CAPABILITIES` entry (see
      [adding-a-tool.md](../guides/adding-a-tool.md)) — this is not caught by any contract
      test, only by review or by a specialist silently failing to use the tool later
- [ ] A new or changed `Capability`'s approval/risk classification was actually reasoned
      about, not left to fall through to a default — see
      [tools-skills-and-specialists.md](../concepts/tools-skills-and-specialists.md) for
      what "risk in a non-production environment" and "risk in production" both mean for
      the change
- [ ] Documentation was updated to match — see
      [documentation-guidelines.md](documentation-guidelines.md) for exactly which file(s)
      a given kind of change should touch
- [ ] No secret value was committed, including inside a test fixture or a migration's
      seed data

## After merge

There is no deployment automation triggered by a merge (see
[operations/deployment.md](../operations/deployment.md)) — deploying, migrating the
production database, and restarting the worker scripts are all separate, manual steps
that follow at whatever cadence your environment uses.
