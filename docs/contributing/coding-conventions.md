# Coding conventions

No `STYLE.md` exists in this repository — these are the conventions actually configured
and observed, verified against the real config files and a sample of real modules, not
invented.

## Backend (Python)

Configured in `backend/pyproject.toml`:

- **Ruff**: `line-length = 120`, `target-version = "py312"`, `select = ["E", "F", "I",
  "UP", "B", "SIM"]`, `ignore = ["E501"]` — line length itself is explicitly not enforced
  by the linter (the project's own comment explains long single-line dependency-wiring
  calls are pervasive and addressed by package structure, not reformatting).
- **Mypy**: `python_version = "3.12"`, `warn_unused_ignores = true`,
  `warn_redundant_casts = true`, `ignore_missing_imports = true`.

Run both before proposing a change:

```bash
cd backend && ruff check . && mypy app
```

### Observed docstring style

Every sampled module carries a module-level docstring — this is consistent enough across
the codebase to treat as a real convention, not just a few examples. The pattern splits in
two, by module complexity:

- **Simple modules** get a single-line docstring stating what the module does:
  `"""A small, safe arithmetic calculator tool."""` (`app/tools/calculator.py`).
- **Modules encoding a non-obvious rule or trade-off** follow the one-line summary with a
  blank line and a longer rationale paragraph explaining *why*, not just what —
  `app/tenancy/service.py` opens with a one-line summary, then explains where role
  comparisons live and why reactivation isn't a supported flow. Match this pattern:
  write the rationale paragraph when there's a non-obvious constraint or trade-off behind
  the code, and skip it when there genuinely isn't one — most migration files and several
  security modules follow the same shape for the same reason.

Don't add a rationale paragraph that just restates the code in prose; that's what the
single-line form is for.

## Frontend (TypeScript)

Configured in `frontend/eslint.config.mjs` (flat config, `eslint-config-next/core-web-vitals`,
no custom rule overrides) and `frontend/tsconfig.json` (`"strict": true`, target ES2017,
`moduleResolution: "bundler"`, path alias `@/*` → `./src/*`).

```bash
cd frontend && npm run lint && npm run typecheck && npm run format
```

## Naming and structure patterns worth following

- **One tool/skill/specialist/template per directory or file**, matching the pattern
  already established — see [repository-structure.md](../reference/repository-structure.md)
  for exactly where each kind of extension lives.
- **`extra="forbid"` on every Pydantic contract that represents an external or
  filesystem-loaded shape** (tool arguments, skill/specialist metadata, chart specs,
  report template metadata/theme) — this is the pattern used everywhere such a contract
  exists in this codebase, and it's what turns a typo'd or stray field into an immediate,
  loud validation error instead of a silently-ignored key.
- **Never hand-copy machine-generated files.** `docs/METRICS.md` and
  `frontend/src/types/api.generated.ts` both carry "do not hand-edit" headers backed by a
  contract test (`test_metrics_doc_snapshot.py`, `test_openapi_snapshot.py`) — always
  regenerate them via their documented command instead of editing directly.

## What this repository does not enforce automatically

There is no pre-commit framework, no git hook, and no CI — none of the above is checked
before a commit or a merge. See [pull-requests.md](pull-requests.md) for what a reviewer
should verify by hand in the absence of automation.
