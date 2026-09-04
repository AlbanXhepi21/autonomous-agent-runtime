---
name: reporting-feature
description: Implement a change to autonomous-agent report compilation, report blocks, templates, themes, PDF or DOCX generation, Matplotlib report charts, evidence appendices, narrative freshness, parameterized reruns, artifact publishing, report preview, or template suitability. Do not use for generic UI styling, a standalone API contract change, or an explanation of reporting architecture.
---

# Reporting feature

## Workflow

Follow this order:

```text
Identify affected report layer
→ inspect canonical contract and invariants
→ inspect both renderer consumers
→ implement at the correct shared layer
→ add structural and content tests
→ generate real sample outputs
→ read back PDF/DOCX
→ render representative pages
→ inspect layout and evidence
```

1. Identify whether the change belongs in compilation/blocks, template structure, theme, rasterization, writer, rerun, publishing, artifact, preview, or suitability behavior. Inspect the compiler and both document consumers before editing.
2. Preserve these invariants:
   - Publish completed runs without reaching `app.llm`; one canonical compiled report feeds PDF and DOCX.
   - Keep renderers from retrieving run-level facts. Preserve resolved provenance for every displayed fact; remove unknown IDs from displayed/resolved evidence while retaining existing unresolved diagnostics.
   - Allow presentation only to filter, reorder, relabel, and format. Do not sum, average, derive, or invent facts. Keep charts data-only and render document charts server-side with Matplotlib.
   - Exclude another-period narrative or visibly mark it stale. Keep PDF authoritative and inspect both PDF and DOCX after generation.
3. Implement at the shared layer that owns the behavior; do not add format-specific fact selection or duplicate rendering logic.
4. Add structural and content tests. Generate representative outputs, read back PDF/DOCX content, render representative pages, and inspect layout, evidence, and stale-narrative behavior.

## Conditional references

- Read [report invariants](references/report-invariants.md) for compiler, renderer, publishing, artifact, and preview constraints.
- Read [testing map](references/testing-map.md) for targeted checks; use `cd backend && .venv/bin/python -m scripts.preview_reports [output_dir]` when layout is in scope.
- Read [tenant isolation](references/tenant-isolation.md) for report/artifact workspace access.

## Stop and ask

Stop if the requested presentation needs new factual derivation, evidence is unavailable or unresolved, a template requirement is ambiguous, output review cannot run, or the change would weaken provenance, tenant scope, or PDF-authoritative policy.

## Completion report

State: changed report layer and invariant coverage; tests and generated-output inspection; evidence/narrative status; PDF/DOCX results; risks, skipped checks, or blockers.
