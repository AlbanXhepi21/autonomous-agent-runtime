# Development workflow

There is no `CONTRIBUTING.md`, no CI, and no git hooks in this repository (all verified
absent by direct search). This page describes the conventions actually observed in the
project's own history and enforced by its own tests — treat the "observed" sections as
description, not policy someone is required to follow, since nothing mechanically enforces
them.

## Branch workflow (observed, not enforced)

`git branch -a` shows a `<type>/<slug>` naming pattern for most branches:
`feat/v3-memory`, `chore/initial-project-structure`, `backup/auth-tenancy-before-rebase`,
`backup/before-remove-next-cache`, `backup/pre-report-commits`. The current working branch
at time of writing (`restructure`) is a counter-example with no prefix — the convention is
observed, not mechanically required. There is no branch-protection or PR-template
configuration in the repository to enforce a naming scheme.

Commit messages are lowercase, imperative-mood, sentence-style (`"Rewrite README as
reference documentation"`, `"Extract the delegation step behind an explicit run-control
seam"`) — not strict Conventional Commits, though some commits do use a `feat:`/`chore:`
prefix and some don't. There is no commit-message linting.

## Code organization

Follow the package boundaries described in
[backend.md](../architecture/backend.md#package-boundaries) — new backend code should
land in the package that already owns its concern (a new tool in `app/tools/`, a new
persistence method in the owning domain package, never a new cross-cutting import into
`app/contracts/` or `app/core/` from outside those two). These boundaries are enforced by
`backend/tests/contracts/test_package_boundaries.py`, which will fail the whole suite on
an introduced import cycle or a leaf-package violation — this is not a style suggestion,
it's a test.

## Contract and package boundaries in practice

Before adding a new top-level backend package, ask whether the concern really doesn't fit
an existing one — 25 packages already exist (see
[repository-structure.md](../reference/repository-structure.md)), each with a specific
job. If you do add one, give it a real module docstring stating its purpose (see
[coding-conventions.md](coding-conventions.md)) — three of the existing packages
(`runtime`, `tools`, `skills`) currently carry stale placeholder docstrings from early
scaffolding that no longer describe what they actually do; don't repeat that mistake.

## Migration conventions

See [database-migrations.md](../guides/database-migrations.md) in full. In short:
hand-written, never `--autogenerate`d; named `YYYYMMDD_NNNN_description.py` with a
globally incrementing counter; every migration implements a real `downgrade()`, even when
that downgrade can only partially restore data (documented in the function's own
docstring when so).

## Test expectations

There is no CI to catch a missed test — a human reviewer is the enforcement mechanism (see
[pull-requests.md](pull-requests.md)). At minimum, before proposing a change:

```bash
cd backend && .venv/bin/python -m pytest       # database-marked tests skip cleanly
cd backend && ruff check . && mypy app
cd frontend && npm run lint && npm run typecheck && npm test
```

If the change touches a backend/frontend contract boundary (a route, a response schema),
also run the database-backed suite and regenerate the OpenAPI snapshot — see below.

## OpenAPI regeneration

Any change to a route, request schema, or response schema requires:

```bash
cd frontend && npm run gen:api
```

`backend/tests/contracts/test_openapi_snapshot.py` fails the suite otherwise, with the
message *"The API schema changed but frontend/openapi.json was not regenerated."* This is
one of the few places a forgotten step produces a hard, unambiguous test failure rather
than a silent drift — rely on it, but don't skip running the suite locally and assume it'll
be caught elsewhere, since there is no CI to catch it for you.

## Documentation update expectations

See [documentation-guidelines.md](documentation-guidelines.md) for what to update and
where, matched to what kind of change you made.

## Repository-local coding-agent skills

The canonical skills live in [`.agents/skills/`](../../.agents/skills/). Claude Code sees
the same content through relative symlinks in [`.claude/skills/`](../../.claude/skills/);
do not copy a skill into both locations.

| Skill | Use for |
|---|---|
| `implement-feature` | A bounded feature after acceptance criteria are clear |
| `fix-bug` | A reproducible defect with concrete evidence |
| `change-api` | Routes, API schemas, OpenAPI/types, frontend API calls, or SSE contracts |
| `database-migration` | Application-schema and Alembic changes |
| `reporting-feature` | Compilation, templates, rendering, evidence, reruns, or report artifacts |
| `verify-change` | A scoped final review before a commit or pull request |

Invoke a Codex skill explicitly with `$skill-name`; invoke the Claude Code link with
`/skill-name`. Both agents may also select a matching skill automatically. Keep skill
instructions procedural and short; put optional repository routing in `references/`.
Update only the canonical directory, validate its `SKILL.md` with the installed skill
validator, verify its `.claude/skills/` relative link, and forward-test it on a read-only
task before relying on a workflow change.
