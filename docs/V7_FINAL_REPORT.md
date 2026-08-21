# V7 Runtime Review

## Architecture

```text
FastAPI → AgentRunner → Context / LLMDecision → Actions
                         ├─ ToolExecutor → environment / artifacts
                         ├─ SkillRegistry
                         ├─ MemoryRetriever / MemoryWriter
                         └─ Delegation → isolated child AgentRunner
                                      ↓
Security policy / approvals → sanitized RunTrace → evals / trajectory / metrics
```

The runtime remains provider-neutral outside `app/llm`, and FastAPI remains an adapter.
`AgentRunner` is the main orchestration object; its dependencies are explicit, while
tools, security policy, memory stores, and child agents retain their own boundaries.

## Deterministic benchmark

Executed with `python -m app.evals.runner --all` using scripted local LLMs on 2026-08-19.

| Suite | Cases | Passed |
| --- | ---: | ---: |
| basic | 3 | 3 |
| tools | 2 | 2 |
| skills | 2 | 2 |
| memory | 1 | 1 |
| delegation | 1 | 1 |
| security | 1 | 1 |
| environment | 1 | 1 |
| reliability | 3 | 3 |
| **Total** | **14** | **14 (100%)** |

| Metric | Average | Median | P95 |
| --- | ---: | ---: | ---: |
| iterations | 1.64 | 2 | 2 |
| LLM calls | 1.79 | 2 | 2 |
| tool calls | 0.50 | 0.5 | 1 |
| delegation calls | 0 | 0 | 0 |
| wall latency (ms) | 5.36 | 2 | 54 |

Tokens and estimated cost are unavailable for the scripted clients, so they are
reported as `null`, not estimated. The 54 ms P95 reflects the intentional retry
backoff in the transient-timeout case.

## Findings

- Tool use was bounded: 7 tool calls across 14 cases; the unsafe calculator case
  was rejected and not runtime-retried.
- No duplicate-action or unnecessary-delegation trajectory violation occurred in
  the bundled deterministic cases.
- Delegation coverage currently proves the trivial no-delegation path only; it is
  not a controlled single-agent versus multi-agent effectiveness comparison.
- Memory coverage proves the transient calculation path. Retrieval relevance and
  durable-writing effectiveness need controlled fixtures before causal claims can
  be made.
- Security coverage confirms policy decisions and safe calculator rejection, but
  approval, injection, secret-extraction, and escalation scenarios remain unit-test
  coverage rather than end-to-end benchmark cases.
- Reliability coverage confirms timeout recovery, one invalid-output repair, and a
  permanent tool failure. Retry exhaustion and policy fail-closed behavior are
  covered by unit tests.

## Hardening completed during review

`InMemoryTraceStore` now has bounded LRU retention (default 1,000 traces). Traces
remain non-persistent and disappear on restart; eviction means old trace URLs may
return 404. This prevents an otherwise unbounded process-memory collection.

## Production-readiness gaps

- In-memory traces are not durable and have no authenticated multi-tenant access
  control.
- OpenAI GPT-5.4+ pricing is versioned in `app/llm/pricing.py`; unsupported provider
  models intentionally remain unpriced rather than receiving a guessed estimate.
- No real-model benchmark is included in automated tests. Use the existing API or
  an injected `LLMClient` manually with a configured provider, then compare the
  generated `EvalResult` fields: pass status, trajectory score, tokens, cost, and
  latency.
- The bundled datasets are deterministic behavior checks, not semantic answer
  quality benchmarks or load tests.
- PostgreSQL migration, approval persistence, and workspace/artifact cleanup need
  environment-specific operational monitoring before unsupervised production use.

## Highest-priority next steps

1. Add controlled end-to-end fixtures for memory, approvals, delegation, and
   environment operations.
2. Add persistent, access-controlled trace storage before relying on traces for
   incident investigation.
3. Run manual configured-model benchmark baselines before comparing providers.
