---
name: fix-bug
description: Diagnose and fix a reproducible defect in autonomous-agent, including incorrect behavior, regressions, exceptions, failing tests, broken API or frontend behavior, and code-caused data inconsistency. Use only when concrete diagnostic evidence or a reproduction can establish the defect; do not use for a new feature, speculative cleanup, or architecture explanation.
---

# Fix bug

## Workflow

Follow this order:

```text
Understand expected behavior
→ reproduce
→ isolate
→ identify root cause
→ add regression test
→ implement smallest fix
→ run targeted tests
→ inspect adjacent risk
→ inspect final diff
```

1. Establish expected and actual behavior from a failing test, exception, request/response trace, persisted record, or other concrete diagnostic evidence.
2. Reproduce with the smallest reliable test or command before editing. Do not make speculative fixes without reproduction or evidence.
3. Isolate the owning boundary and direct callers. Identify the causal path, not merely a visible symptom.
4. Add a regression test that fails for the diagnosed cause, then make the smallest fix that makes it pass.
5. Run the reproducer and nearest affected tests first. Inspect adjacent contract, tenant, report, or generated-contract risk only when the changed boundary warrants it.
6. Inspect changed files and final diff. Confirm the regression test asserts correct behavior rather than accommodating the defect.

## Guardrails

- Do not broaden into refactoring, suppress errors, weaken validation, or change tests to accept broken behavior.
- Do not add retries until the failure mode and its ownership are understood.
- Do not treat symptoms while knowingly leaving the root cause in place.
- Preserve package, SQL, tenant, report, evidence, and API-generation invariants from the root instructions.

## Conditional references

- Read [testing map](references/testing-map.md) when choosing a reproducer or test tier.
- Read [repository boundaries](references/repository-boundaries.md) only when the causal path crosses packages, routes, or generated contracts.
- Read [tenant isolation](references/tenant-isolation.md) only for authorization, cross-workspace, session, or artifact-access defects.
- Read [report invariants](references/report-invariants.md) only for rendered report output, evidence, charts, publishing, or template behavior; do not load it for artifact persistence alone.

## Stop and report

Stop if the defect cannot be reproduced or evidenced, required credentials/services are unavailable, the operation would be destructive, authorization semantics are unknown, or unrelated tests already fail. Report the evidence, exact blocker, and smallest safe next diagnostic.

## Completion report

State: root cause; smallest fix; regression test; targeted checks and results; adjacent risk checked; remaining risks, skipped checks, or blockers.
