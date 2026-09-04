# Documentation guidelines

This documents how the `docs/` tree itself is organized and how to keep it accurate as
the code changes — the same standard it was written to.

## Structure

| Directory | Purpose | Audience |
|---|---|---|
| `docs/getting-started/` | Verified setup: prerequisites, local dev, configuration, troubleshooting | New contributors |
| `docs/architecture/` | System-level design: how packages fit together, request lifecycles, trust boundaries | Contributors making non-trivial changes |
| `docs/concepts/` | Feature-level explanations built from live registries/contracts | Anyone extending a specific feature |
| `docs/reference/` | Flat lookup material: structure, env vars, commands, permissions, limitations | Everyone, for quick lookup |
| `docs/guides/` | Step-by-step "how to add/run X," referencing real contracts | Contributors doing a specific task |
| `docs/api/` | HTTP contract reference | Frontend/integration developers |
| `docs/operations/` | Deployment, database, observability, security, retention, readiness | Whoever operates a deployment |
| `docs/contributing/` | This directory | Contributors |
| `docs/TENANCY.md`, `DATASOURCES.md`, `METRICS.md` | Pre-existing, machine-generated or independently maintained references | Everyone |

`docs/README.md` is the index — every document must be linked from it before it's
considered part of the set; don't leave a new file orphaned.

## Never hand-edit generated files

Two files are regenerated from code and carry "do not hand-edit" headers, each backed by
a contract test that fails the suite if they drift from source:

- `docs/METRICS.md` — regenerate with `python -m scripts.generate_metrics_doc` from
  `backend/` after any change to `backend/app/analytics/semantics/metrics.py`
  (`test_metrics_doc_snapshot.py` enforces this).
- `frontend/openapi.json` (consumed by `frontend/src/types/api.generated.ts`) —
  regenerate with `npm run gen:api` from `frontend/` after any route/schema change
  (`test_openapi_snapshot.py` enforces this).

Everything else under `docs/` is hand-maintained prose and must be updated manually — no
test enforces documentation accuracy for hand-maintained files, which is exactly why the
next section matters.

## What to update for a given kind of change

| You changed... | Update... |
|---|---|
| A tool's behavior, or added one | [tools-skills-and-specialists.md](../concepts/tools-skills-and-specialists.md), and [adding-a-tool.md](../guides/adding-a-tool.md) if the *process* of adding a tool changed |
| A skill or specialist | The matching table in [tools-skills-and-specialists.md](../concepts/tools-skills-and-specialists.md) |
| A metric's definition or status | Regenerate `docs/METRICS.md`; hand-update the summary table in [semantic-metrics.md](../concepts/semantic-metrics.md) |
| A chart type or `ChartSpec` field | [charts-and-displays.md](../concepts/charts-and-displays.md) |
| A report template | [report-templates.md](../concepts/report-templates.md) |
| A route, request/response schema | Regenerate `frontend/openapi.json`; update the matching file in `docs/api/` |
| An environment variable | Both [configuration.md](../getting-started/configuration.md) and [environment-variables.md](../reference/environment-variables.md) — they intentionally overlap (setup narrative vs. quick reference) and must be kept in sync by hand, since nothing else keeps them in sync |
| A permission or role | [permissions.md](../reference/permissions.md) |
| A migration | Nothing doc-wise beyond [database-migrations.md](../guides/database-migrations.md) if the *convention itself* changed |
| Anything that closes a documented limitation | Remove or correct the entry in [limitations.md](../reference/limitations.md) — a stale limitation is as misleading as a missing one, and this repository already has two known examples of exactly that (README's stale metric count and stale retention claim, both documented in that file) |

## Verified, not assumed

Every fact in this documentation set was checked against the actual code, a real test, or
a real config file at the time it was written — not inferred from a docstring or a
comment alone, and never copied from another document without re-verification when the
underlying code was in scope for that pass. Keep this standard: when you update a doc
because code changed, re-check the specific line/behavior you're documenting rather than
adjusting prose around it based on assumption.

When a docstring or comment claims something you can't find an enforcing check or test
for, say so explicitly in the document (see, e.g., the "claimed but not verified as
enforced" framing used throughout [data-analysis.md](../architecture/data-analysis.md))
rather than stating it as settled fact.

## Link and formatting conventions

- Relative links only, resolved from the linking file's own directory (e.g. from
  `docs/guides/`, a link to a concepts page is `../concepts/foo.md`, not `concepts/foo.md`).
- A path containing literal parentheses (e.g. Next.js's `(app)/layout.tsx` route group)
  must be wrapped in angle brackets — `[text](<../../frontend/src/app/(app)/layout.tsx>)`
  — or GitHub's Markdown parser closes the link at the first unescaped `)`.
- Every heading you link to via an anchor should be checked against GitHub's slugification
  (lowercase, strip punctuation, spaces to hyphens) — when in doubt, avoid punctuation in a
  heading you intend to link to from elsewhere, since it keeps the anchor predictable.
- No absolute local filesystem paths, no real secret values — every code example uses a
  placeholder (`sk-REDACTED`, `<workspace-id>`, etc.).
- Reference real files with relative links; don't reproduce large source excerpts —
  quote only what's essential to make a point precisely (a short function signature, a
  key validation branch), and cite the file:path for the rest.

## Validating before you're done

There is no automated link checker wired into this repository's tests. Before considering
a documentation change complete, verify by hand (or with a small script) that:
- Every relative link resolves to a real file.
- Every anchor link resolves to a real heading in the target file.
- Every referenced repository file/path actually exists.
