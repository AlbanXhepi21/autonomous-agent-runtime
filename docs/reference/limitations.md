# Known limitations

Every item below was checked against current code in this documentation pass, not copied
from another document without verification. Where the project's own `README.md` states a
limitation that no longer matches the code, that's called out explicitly as a
**documentation discrepancy**, distinct from a genuine current limitation.

## The production security environment is a near-total kill switch, not a tightening

This is the most consequential finding in this documentation pass and was not previously
documented anywhere in the repository. Setting `SECURITY_ENVIRONMENT=production` does not
merely tighten a few controls — `RiskClassifier._is_production_target()` treats "the
environment itself is set to production" as sufficient to classify **every single action**
as targeting a production-like resource, checked before any capability-specific logic
runs at all. The practical effect:

- Every read-only tool (`list_files`, `read_file`, schema/metric lookups,
  `get_repository_tree` and friends) and every analytics tool (`query_database`,
  `analyze_dataset`, `create_chart`, `generate_report`) — all of which auto-allow at LOW
  or MEDIUM risk in any other environment — become `CRITICAL` risk and are **denied
  outright** in production.
- Only the four capabilities already gated for human approval
  (`write_file`, `run_command`, `python_exec`, `register_artifact`) continue to work at
  all in production, and only via approval — because their approval gate is checked
  before the risk table is ever consulted, it never sees the production-wide override.
- `update_investigation_plan` is the one action unaffected either way, because it bypasses
  the capability/risk system entirely via a primary-agent compatibility rule.

See [tools-skills-and-specialists.md](../concepts/tools-skills-and-specialists.md) for the
full per-tool breakdown. Treat `SECURITY_ENVIRONMENT=production` as effectively disabling
unattended agent operation, not as a normal deployment-environment label, until this is
either the intended design or revisited.

## Unimplemented web-search provider

`WebSearchTool` (`backend/app/tools/web_search.py`) has a real argument schema and a real
`Capability.WEB_SEARCH` mapping, but `execute()` unconditionally raises
`NotImplementedError`, and — more significantly — it is **never registered** in
`get_tool_registry()`, so it is unreachable by the running agent regardless of the stub.
Confirmed by grep across the entire `composition/` tree. The `research` specialist's empty
`allowed_tools` list is a direct downstream consequence: it currently has no way to gather
external evidence at all.

## Documentation-only metrics

9 of the 28 registered semantic metrics have no compiled SQL and are guidance-only — the
agent must write its own query, validated the same way as any other agent-authored SQL.
Full status breakdown, verified against `backend/app/analytics/semantics/metrics.py`
today: **5 `production_ready`, 14 `validated`, 0 `executable`, 9 `documented`** — 19 of 28
compile to a rerunnable statement. See
[semantic-metrics.md](../concepts/semantic-metrics.md).

**Documentation discrepancy**: the root `README.md`'s "Status and known limitations"
section currently states *"Five of twenty-two metrics have compiled SQL definitions... The
remaining seventeen stay documentation for the agent."* Both numbers are stale against the
current registry — there are 28 metrics today, not 22, and 19 compile (production_ready +
validated), not 5. The registry itself and `docs/METRICS.md` (machine-regenerated from it)
are authoritative; README has not been updated to match.

## Display-generation limitations

- **No filter or sort field exists on `ChartSpec`** — any filtering/ordering must already
  be baked into the SQL that produced the chart's data.
- **The agent tends to produce one display per run in practice**, per the project's own
  README, even though the coded ceiling is 8 charts per run and the suggested budget for
  a `detailed_report` request is 5–8. This is an observed behavioral tendency, not an
  enforced limit — see [charts-and-displays.md](../concepts/charts-and-displays.md).
- **Two independently maintained chart renderers** (Recharts in the browser, Matplotlib on
  the server for PDF/DOCX) share a data contract but no rendering code — a layout change
  must be replicated by hand in both places.
- `executive_dashboard`'s `primary_breakdown` slot is both required and hard-capped at
  exactly one chart, which interacts poorly with the one-display-per-run tendency above —
  see [report-templates.md](../concepts/report-templates.md).

## Retention sweeper status

**Implemented, and this corrects a stale claim.** `backend/scripts/run_artifact_retention.py`
sweeps expired, `standard`-policy, `READY` artifacts safely across multiple worker
processes, deletes their bytes, and marks them `DELETED` with the row kept as an audit
trail. It is a real, working worker — not a design-only stub.

**Documentation discrepancy**: the root `README.md` states in two places (its
configuration section and its "Status and known limitations" section) that
*"nothing currently sweeps expired artifacts."* This was true at some earlier point in the
project's history but is no longer accurate — the sweep script exists and works today. What
*is* still true, and worth stating precisely instead: **nothing in this repository starts
that worker automatically.** It must be run explicitly — via cron, a process manager, or
similar — by whoever operates the deployment. See
[artifacts.md](../concepts/artifacts.md) and [commands.md](commands.md).

## Connector limitations

Only PostgreSQL is supported as a data source — both the process-wide demo database
(`ANALYTICS_DATABASE_URL`) and workspace-connected sources (`backend/app/datasources/`).
No CSV upload, and no warehouse connectors (Snowflake, BigQuery, Redshift, Databricks) —
confirmed by the complete absence of any such reference anywhere in `app/datasources/`.
Additionally:

- The process-wide demo connection has **no role-level read-only verification** — unlike
  workspace-connected sources (which both check role privileges and live-probe that
  PostgreSQL rejects a write), the demo connection's read-only guarantee rests solely on
  the per-query `SET TRANSACTION READ ONLY` statement.
- Semantic metrics and parameterized reruns are not available against
  workspace-connected sources at all — both operate only against the fixed demo schema.
- Column sensitivity classification (e.g. "authentication_secret," "personal_data")
  affects only whether example values may be *sampled* during profiling — it has no
  effect on whether a column can be *queried*. Only the separate, boolean `excluded` flag
  reaches the SQL validator.

## Authentication features not yet implemented

Verified by reviewing every method on `AuthService`
(`backend/app/identity/service.py`) and grepping the codebase for common alternative
auth mechanisms. What exists: registration, login/logout (single and all-sessions), email
verification, forgot/reset password, authenticated password change — all cookie-session
based with Argon2id hashing. **What does not exist, confirmed absent, not merely
undocumented:**

- No OAuth/social login (Google, GitHub, etc.) and no SAML/SSO integration.
- No multi-factor authentication (TOTP, WebAuthn, SMS, or otherwise).
- No passwordless/magic-link login.
- No account lockout beyond the existing per-IP rate limiting on login/register attempts.

## Other verified limitations worth knowing

- **`POST /api/v1/invitations/accept` has no CSRF protection**, inconsistent with every
  other mutating route in the same file — see
  [authentication-and-tenancy.md](../architecture/authentication-and-tenancy.md#csrf-behavior).
- **`SECURITY_ENVIRONMENT` only forces `Secure` cookies for the literal value
  `production`** — the default `unknown`, plus `development` and `staging`, do not, which
  is easy to leave misconfigured in a real non-local deployment.
- **No durable trace storage** — the detailed, step-by-step record of what an agent run
  did (every LLM call, tool call, retry) is process-local and lost on restart, bounded to
  the most recent 1,000 traces. Only a denormalized summary survives on the run record.
- **No vector/semantic memory search** — retrieval is lexical token-overlap; a
  conceptually related memory phrased differently will not surface.
- **No Docker, no CI, and no end-to-end browser test suite** exist anywhere in this
  repository — verified absent by direct filesystem search, not merely undocumented.
- **`ARCHITECTURE.md` at the repository root is stale** — it describes a pre-restructure
  package layout (`app/agent/`) that no longer exists; use
  [architecture/overview.md](../architecture/overview.md) instead.
- **A package-boundary test still checks for an import of a package name (`app.agent`)
  that no longer exists** in the codebase, making that specific check a permanent no-op —
  see [architecture/backend.md](../architecture/backend.md#known-inconsistencies).
- **Two independent secret-redaction implementations** exist doing the same job by
  different code paths (`app/core/logging.py` and
  `app/security/credentials.py::SecretRedactor`).
- **Prompt-injection defenses are heuristic and diagnostic only**, per the codebase's own
  design — they label suspicious content, they do not block or rewrite it, and the project
  itself states injection resistance has not been benchmarked end-to-end.
- **Development-grade controls, per the project's own README**: the credential provider,
  approval endpoints, restricted Python/command execution, and file-backed approval
  locking are explicitly described as not yet hardened for unsupervised production use of
  sensitive tools.
