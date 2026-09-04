---
name: implement-feature
description: Implement a bounded new feature or enhancement in autonomous-agent. Use for requests to add user-visible behavior, a capability, or a focused vertical slice. Do not use for a defect/regression, a primarily API-contract change, a database migration, or a reporting-specific change when its specialized project skill is available.
---

# Implement feature

## Workflow

1. Translate the request into observable acceptance criteria, non-goals, and affected user or tenant boundary.
2. Classify the work before exploring implementation details:
   - API request/response or route change: use the `change-api` skill.
   - Persisted schema change: use the database-migration skill.
   - Template, publish, artifact, PDF, or DOCX behavior: use the reporting-feature skill.
   - Otherwise, continue here. If a required specialized skill is unavailable, state that boundary and follow only the shared rules; do not recreate its procedure.
3. Stop for unclear acceptance criteria or an architecturally significant ambiguity before loading conditional references or selecting an extension point.
4. Identify the smallest owning package, feature, route, or component. Search for an existing pattern with `rg`; inspect only its direct callers, contracts, and colocated tests.
5. Write a short plan naming the owner, changed boundary, tests, generated outputs, and explicit non-goals.
6. Implement the smallest complete vertical slice. Follow the nearest established pattern; do not broaden into unrelated cleanup.
7. Add or update tests for the acceptance criteria. Run the closest test first, then only the adjacent contract or broader check justified by changed boundaries.
8. Inspect changed files and the final diff. Confirm generated outputs, documentation, and risks before reporting.

## Required checks

- After the request is actionable, read [repository boundaries](references/repository-boundaries.md) only before changing backend ownership, imports, routes, or generated contracts.
- Read [tenant isolation](references/tenant-isolation.md) only for workspace-owned data, permissions, sessions, or artifact access.
- Read [testing map](references/testing-map.md) only when selecting or expanding tests.

## Stop and ask

- The request has architecturally significant ambiguity, a new cross-cutting owner, or unclear acceptance criteria.
- A stateful endpoint or resource lacks a defined authorization or tenant scope.
- The requested action is destructive, needs unavailable credentials, or could affect data outside the stated scope.
- A failing test is unrelated to the changed behavior; report it instead of fixing it opportunistically.
- The necessary change expands beyond the agreed acceptance criteria. Present the discovered scope and request direction.

## Completion report

State: changed behavior and files; acceptance criteria covered; tests run and results; generated outputs or documentation updated; remaining risks, skipped checks, or blockers.
