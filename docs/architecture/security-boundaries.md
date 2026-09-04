# Security boundaries

This document walks the trust boundaries a request or a piece of data crosses as it moves
through the system, and states plainly where a boundary is a real enforcement gate versus
a label or a documented convention. It complements
[agent-runtime.md](agent-runtime.md#human-approval-checkpoints) (approval gating) and
[authentication-and-tenancy.md](authentication-and-tenancy.md) (the auth/tenant boundary)
rather than repeating them.

## User input → LLM

There is effectively no sanitization boundary here today. A submitted goal or chat message
only needs to be non-empty; it flows into the agent's context and to the model unmodified.
There is no prompt-injection filtering or content stripping applied to the user's *own*
initiating text — that risk is treated differently from tool-fetched content (see
[External content](#external-content) below), which does carry a trust label.

## Model output → runtime

Every action the model returns must parse into a validated `AgentAction`
(`backend/app/contracts/actions.py`) before it can be dispatched — required fields are
enforced per action type (a `use_tool` action without `tool_name` cannot be constructed; a
non-`finish` action carrying citations or caveats cannot be constructed). If the provider
returns something that doesn't parse into this shape at all (no function call, unparseable
arguments), that's treated as invalid model output and retried — dispatch never runs on a
malformed action.

## Tool arguments

Validated **twice, independently**: once by the LLM provider's own function-calling
contract (each tool's schema is sent to OpenAI so it only ever proposes matching
arguments), and again, server-side, by the tool executor itself — a hand-rolled check of
required fields, rejection of unexpected extra fields, and primitive type checking. The
second check runs regardless of whether the first one already caught a problem; nothing
here depends on trusting the provider's enforcement alone.

## SQL

Covered in full in [data-analysis.md](data-analysis.md#sqlglot-ast-validation) — every
agent-written or metric-compiled query is parsed to an AST and checked against a
statement-shape rule, a node-type blocklist, a dangerous-function blocklist, and a
schema/table/column allowlist before it can execute, inside a read-only transaction with a
server-enforced timeout.

## Filesystem

`WorkspacePathPolicy` (`backend/app/environment/policies.py`) rejects any absolute path
outright, then resolves the candidate relative to the workspace root and checks the
*resolved* result is still contained within that root. Resolving before checking
containment is what makes this correct against both `..` traversal and symlink escapes —
a naive string check for `..` alone would miss a symlink that points outside the root
without ever containing the literal string `..`.

## External content

The runtime has a real trust-labeling mechanism for content a tool fetches from outside
the system — `backend/app/security/trust.py` tags output from `read_file` and
repository-inspection tools as `UNTRUSTED_EXTERNAL`, and provides heuristic
prompt-injection-pattern detection over such content. Two things are worth being precise
about:

- This mechanism is a **label plus a heuristic diagnostic**, not an enforcement gate. Its
  own code is explicit that the injection-pattern check is never an authorization result —
  it doesn't block or rewrite anything, it only flags.
- The boundary is currently **moot for web content specifically**: `web_search` is an
  unimplemented placeholder (see [`../README.md`](../README.md) and
  [backend.md](backend.md)) that is not even registered as a callable tool. The trust
  classification that would apply to search results is defined in code but has no live
  content to ever apply to today.

## Credentials

Two independent mechanisms exist, worth naming as separate rather than one shared system:

- **`SecretReference`/`CredentialProvider`** (`backend/app/security/credentials.py`) —
  trusted integrations (OpenAI, the runtime database, GitHub, SMTP, data-source
  encryption) are referred to by a validated logical name, never a raw value, and resolved
  from the process environment only at the moment they're needed. A successfully resolved
  secret is registered into a known-secrets set used for redaction.
- **Redaction** — `redact_secret_text()` (`backend/app/core/logging.py`) strips every
  known resolved secret plus pattern-matches common credential shapes (API keys, Bearer
  tokens, PEM private-key headers) wherever it's actually called: at logging call sites,
  and — importantly — on tool output *before* it's kept as an agent observation, so a
  leaked credential in a tool's raw output doesn't get replayed back into the model's own
  context. A second, independent redaction implementation
  (`SecretRedactor` in `credentials.py`) exists alongside this one, doing the same job
  with the same technique but as separate code — not a shared implementation.
  Redaction depends on call sites choosing to use these helpers; there is no single
  centralized point that guarantees every future log line or trace field is routed through
  it.

See [configuration.md](../getting-started/configuration.md) for the related, separate
finding that two of these logical references (`SMTP_PASSWORD`, `GITHUB_TOKEN`) are read
directly from the process environment and are **not** picked up from `backend/.env` the
way every other setting is.

## Tenant context

The full mechanism is in [authentication-and-tenancy.md](authentication-and-tenancy.md).
The short version: an authenticated user is not automatically authorized inside a given
workspace — `get_tenant_context` is the one resolver that turns "signed in" into "signed
in, and a member of this workspace, with this role," and store-level queries independently
re-scope by `workspace_id` beneath it.

## Report publishing

Publishing a saved report does not re-check permissions or tenant ownership at its own
execution layer — it trusts that the report definition it was handed was already fetched
through an upstream, workspace-scoped store call (which, today, it always is: the API
route requires `PUBLISH_REPORTS` permission and fetches the definition scoped to the
caller's own workspace before execution ever begins). If a future code path ever
constructed or passed in a report definition without going through that scoped fetch,
nothing inside the execution service itself would catch a mismatched workspace — the
correctness here is inherited from the caller, not independently re-verified.

## Evidence resolution

A citation that doesn't resolve to a real, executed query in the run's trace is neither
silently dropped nor rejected outright — it's separated into its own "unresolved" list,
distinct from the resolved evidence actually attached to the answer, and logged as a
structured event. The answer itself is not blocked on this; whether an unresolved citation
is ever surfaced to the end user or into a published report (versus staying only in the
logs) was not confirmed in the files reviewed for this document.

## Known gaps found while documenting these boundaries

- **`POST /api/v1/invitations/accept` has no CSRF protection** — see
  [authentication-and-tenancy.md](authentication-and-tenancy.md#csrf-behavior).
- **`SECURITY_ENVIRONMENT` only forces secure cookies for the literal value
  `production`** — `staging` and the default `unknown` do not, which is easy to
  misconfigure in a real deployment.
- **Two separate secret-redaction implementations** exist
  (`core/logging.py` and `security/credentials.py::SecretRedactor`) doing the same job by
  different code paths, rather than one shared implementation.
- **The external-content trust boundary has no live content to apply to** — `web_search`
  is unimplemented, so the `UNTRUSTED_EXTERNAL` classification for search results is
  defined but currently unreachable.
- **Injection-pattern detection is heuristic and diagnostic only** — it is explicitly not
  an authorization mechanism in its own code, and should not be described as a
  prompt-injection defense in any other document.
- **Report publishing inherits its authorization correctness from an upstream fetch**
  rather than independently re-verifying workspace ownership at the point of execution.
