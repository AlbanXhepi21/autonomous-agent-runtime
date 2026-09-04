# Adding a tool

## 1. Relevant contract

`Tool` (`backend/app/tools/base.py`) is an ABC with exactly four abstract members:

```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    @property
    @abstractmethod
    def description(self) -> str: ...
    @property
    @abstractmethod
    def arguments_schema(self) -> dict[str, Any]: ...
    @abstractmethod
    async def execute(self, **arguments: Any) -> Any: ...
```

Two more members are **opt-in conventions**, read via `getattr` by the executor, not
enforced by the ABC: `requires_run_id: bool` and `async def execute_for_run(self, *,
run_id, workspace_id, **arguments) -> Any`. `ToolExecutor._run`
(`backend/app/tools/execution/executor.py`) calls `execute_for_run` only when
`getattr(tool, "requires_run_id", False)` is true; otherwise it calls plain `execute`.
Use `execute_for_run` only if the tool needs to scope a side effect (a chart, a report, a
dataset, an artifact) to the run that produced it — see `register_artifact`,
`query_database`, `analyze_dataset`, `create_chart`, and `generate_report` for real
examples.

## 2. Implementation location

`backend/app/tools/` for general-purpose tools, `backend/app/tools/database/` for
anything touching the analytics database. One file per tool (or a small related group,
as `filesystem.py` and `repository.py` do).

## 3. Registration / discovery

There is no filesystem discovery for tools — a new tool is registered by adding one line
to `get_tool_registry()` in `backend/app/composition/providers/tools.py`:

```python
registry.register(YourNewTool(...))
```

`ToolRegistry.register` (`backend/app/tools/registry.py`) keys the tool by its own `name`
property.

## 4. Security or capability requirements

Add an entry to `_TOOL_CAPABILITIES` in `backend/app/security/permissions.py`:

```python
"your_tool_name": Capability.SOME_CAPABILITY,
```

**If you skip this step, the tool silently gets `capability=None`.** For the primary
agent this is harmless — a compatibility rule in `SecurityPolicy.evaluate`
(`backend/app/security/authorization.py`) auto-allows any capability-less action for a
`primary`/`system` subject. But **no specialist can ever be granted the tool**, even if
it's listed in that specialist's `allowed_tools` — `with_specialist()` only grants
capabilities present in `_TOOL_CAPABILITIES`, so a specialist's call would hit
default-deny. There is no contract test that catches a missing entry — this is verified
only by whichever specialist/unit test actually exercises the tool, so add one.

If the tool should require human approval, it needs a `Capability` value already covered
by `with_human_approval_gates()`'s default list (`FILESYSTEM_WRITE`, `COMMAND_EXECUTE`,
`PYTHON_EXECUTE`, `ARTIFACT_CREATE`) or a change to that call site — see
[agent-runtime.md](../architecture/agent-runtime.md#human-approval-checkpoints). If the
tool has a resource identifier worth checking against production-like patterns (a path, a
command, a table), add a case to `resource_for_tool()` in the same `permissions.py` file.

## 5. Tests required

There is no shared test harness class — tests construct a `ToolRegistry()` and
`ToolExecutor(registry)` inline. Follow the pattern in
`backend/tests/unit/tools/test_tools.py` (where `calculator`'s tests live, alongside
throwaway `EchoTool`/`FailingTool` subclasses used to test generic executor behavior):

- Construct the tool directly and call `await tool.execute(...)` (or
  `execute_for_run(...)`) with valid arguments — assert the output shape.
- Assert invalid arguments produce a `ToolInputError` (or fail schema validation) rather
  than an unhandled exception.
- If the tool is run-scoped, assert calling plain `execute()` raises (the existing
  run-scoped tools all do this deliberately).
- If you added a `_TOOL_CAPABILITIES` entry, add a test that exercises the tool through a
  specialist's `allowed_tools` (or add it to an existing specialist's coverage) so a
  missing-capability regression is actually caught — this isn't automatic.

## 6. Documentation required

Add a row to the tool table in
[tools-skills-and-specialists.md](../concepts/tools-skills-and-specialists.md) — name,
purpose, input/output, capability, risk, approval, key limits — using the existing rows as
the format to match. If the tool changes what a specialist can do, update that
specialist's row too.

## 7. Common mistakes

- Forgetting the `_TOOL_CAPABILITIES` entry, which silently blocks every specialist from
  ever using the tool while the primary agent works fine — this asymmetry is easy to miss
  in testing if you only exercise the primary agent path.
- Setting `requires_run_id = True` without implementing `execute_for_run` — the executor
  will call a method that doesn't exist.
- Returning a raw exception message from `execute()` instead of raising `ToolInputError`
  (for bad arguments) or `ToolExecutionError` (for execution failures, which carries a
  `failure_category`) — the executor's generic catch-all replaces an unrecognized
  exception's message with a fixed, non-descriptive string precisely so internals aren't
  leaked, which makes debugging a plain `Exception` harder than it needs to be.
- Not bounding output size — every existing tool enforces some limit (byte count, row
  count, timeout); an unbounded tool can blow through `max_observation_length` truncation
  in an unpredictable way.

## 8. Complete minimal example

A tool that returns the current UTC time — deliberately trivial, matching the real
contracts exactly:

```python
# backend/app/tools/clock.py
"""Returns the current UTC time — a minimal example tool."""

from datetime import UTC, datetime
from typing import Any

from app.tools.base import Tool


class CurrentTimeTool(Tool):
    @property
    def name(self) -> str:
        return "current_time"

    @property
    def description(self) -> str:
        return "Return the current UTC time as an ISO-8601 string."

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "additionalProperties": False}

    async def execute(self, **arguments: Any) -> str:
        return datetime.now(UTC).isoformat()
```

Registration (`backend/app/composition/providers/tools.py`):

```python
registry.register(CurrentTimeTool())
```

Capability (`backend/app/security/permissions.py`):

```python
"current_time": Capability.CALCULATOR_EVALUATE,  # or a new, more specific Capability
```

A minimal test (`backend/tests/unit/tools/test_tools.py`):

```python
async def test_current_time_returns_an_iso_string() -> None:
    result = await CurrentTimeTool().execute()
    datetime.fromisoformat(result)  # raises ValueError if not a valid ISO-8601 string
```
