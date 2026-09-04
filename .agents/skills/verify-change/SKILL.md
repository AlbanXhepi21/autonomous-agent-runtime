---
name: verify-change
description: Review completed autonomous-agent changes, verify an implementation, prepare work for commit or pull request, check feature completeness, or run final validation. Do not use to diagnose an unexplained failing test or implement new functionality; do not automatically fix unrelated findings.
---

# Verify change

## Workflow

1. Inspect `git status --short`, changed files, and the intended scope. If no in-scope diff exists, stop and request a diff, commit range, or worktree; do not run unrelated tests.
2. Map changed paths to risks, then inspect the full diff before running broad checks.
3. Run the closest targeted tests. Add `cd backend && .venv/bin/python -m pytest tests/contracts/test_package_boundaries.py` for backend ownership/import changes.
4. For migrations, inspect `cd backend && .venv/bin/python -m alembic heads`; verify the chain and database-backed coverage only when configuration is available.
5. For routes, schemas, generated types, frontend API calls, or SSE contracts, run the OpenAPI snapshot/type checks and inspect generated-file drift. Run `cd frontend && npm run gen:api` only when regeneration is an intended, authorized part of the reviewed scope; otherwise report drift as a finding.
6. For workspace-owned data or authorization, inspect tenant scope and run the applicable isolation test. For reports/artifacts, inspect report invariants and generated-output checks.
7. Search the changed scope for secrets, debug code, temporary files, accidental generated output, and test weakening without echoing credential values. Do not fix unrelated problems; fix a defect introduced by the current task only when authorized.
8. Report findings by severity and conclude whether the change is ready.

## Conditional references

- Read only the reference indicated by changed paths: [testing map](references/testing-map.md) for test selection; [repository boundaries](references/repository-boundaries.md) for package/API drift; [migration conventions](references/migration-conventions.md) for migration-chain changes; [tenant isolation](references/tenant-isolation.md) or [report invariants](references/report-invariants.md) for those affected domains.

## Final report

Include: scope reviewed; findings grouped by severity; tests run; passed checks; unverified areas; risk assessment; readiness conclusion. Name exact blockers and commands not run.
