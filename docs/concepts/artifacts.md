# Artifacts

An artifact is any durable output file a run produces — a chart PNG from `analyze_dataset`,
a CSV extract or Markdown report from `generate_report`, a manually registered file from
`register_artifact`, or a published PDF/DOCX from report publishing. All of them go through
one shared registration path, `ArtifactStore` (`backend/app/artifacts/`).

## Creation

Every artifact is created by one of:

- `register_artifact` (a tool the model calls directly — **requires human approval**, see
  [tools-skills-and-specialists.md](tools-skills-and-specialists.md))
- `analyze_dataset`, which registers each PNG it generates as a `chart`-type artifact
- `generate_report`, which registers `report.md`, `supporting_metrics.json`, and any
  requested CSV extracts
- Report publishing (`ReportPublisher`), which registers the final PDF/DOCX

In every case, registration is two-phase: a row is created `PENDING`, the bytes are then
copied into storage with a SHA-256 digest computed, and only once that succeeds does the
row become `READY`. A write failure leaves the row `FAILED` rather than a `READY` row
pointing at incomplete or missing bytes.

## Lifecycle states

| Status | Meaning |
|---|---|
| `PENDING` | Registered, bytes not yet confirmed written |
| `READY` | Bytes verified on disk, safe to serve |
| `FAILED` | The write failed |
| `DELETED` | Retention expired and bytes were removed; the row remains as an audit trail |

A row never moves back out of `DELETED` or `FAILED` into `READY`.

## Storage and integrity

Bytes live under a workspace-relative key
(`artifacts/{run_id}/{artifact_id}/{filename}`), with path-escape guards preventing a
crafted name from writing outside that structure, and a blocklist that refuses to
register a file whose name or content looks like it contains secret material. Every
artifact's SHA-256 is computed and stored at write time — see
[persistence.md](../architecture/persistence.md#artifacts).

## Backends

Two implementations exist, selected by `ARTIFACT_BACKEND`
(see [configuration.md](../getting-started/configuration.md)):

- `in_memory` (default) — records live only in the process; **all download links are lost
  on restart**, even though the underlying files may still be on disk.
- `postgres` — the record survives a restart alongside the bytes.

## Retention

Every artifact has a `retention_policy`: `standard` (subject to expiry), `legal_hold`, or
`permanent`. Only `standard` artifacts past their `expires_at` are eligible for deletion —
the retention worker's own query excludes the other two policies at the database level, so
they can't be swept even by a direct, deliberate invocation. Scheduled-report artifacts get
a configurable retention window (`SCHEDULED_REPORT_ARTIFACT_RETENTION_DAYS`, default 90
days); ad-hoc, manually published artifacts get no expiry by default.

**The retention sweeper is implemented, not merely designed.**
`backend/scripts/run_artifact_retention.py` claims expired, `standard`, `READY` artifacts
(using row-level locking so multiple worker processes can run safely against the same
database), deletes their bytes, marks them `DELETED`, and retries a bounded number of
times before giving up on a stubborn deletion. It is **not** started automatically by
anything in this repository — it must be run explicitly, on a schedule, by whoever
operates the deployment (see [commands.md](../reference/commands.md) and
[limitations.md](../reference/limitations.md)).

## Size limits

`MAX_ARTIFACT_BYTES` (default 10 MB) bounds any single artifact — sized deliberately large
enough to admit a full rendered document with embedded charts, not just a text file (see
[configuration.md](../getting-started/configuration.md)).

## Serving

Artifacts are served over `GET /artifacts/{artifact_id}` — a route deliberately not nested
under `/workspaces/{workspace_id}/...` (so a delivered link works without a workspace
prefix), which performs its own manual tenant-ownership check rather than the standard
per-route dependency (see
[authentication-and-tenancy.md](../architecture/authentication-and-tenancy.md#permission-resolution-and-tenant-context-enforcement)).

## Known limitations

- The `in_memory` artifact backend loses every download link on process restart — files
  already on disk become orphaned and unreachable through the API.
- No supervisor bundled with this repository keeps the retention worker running; it must
  be operated externally (cron, a process manager, or similar).
