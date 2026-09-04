# Adding a specialist

## 1. Relevant contract

`AgentMetadata`/`AgentDefinition` (`backend/app/contracts/specialists.py`, `extra="forbid"`):

```python
class AgentRuntimeOverrides(BaseModel):
    max_iterations: int | None = None  # ge=1

class AgentMetadata(BaseModel):
    name: str            # min_length=1, must equal the directory name
    description: str     # min_length=1
    version: str          # min_length=1
    tags: list[str] = []
    allowed_tools: list[str] = []
    allowed_skills: list[str] = []
    runtime_overrides: AgentRuntimeOverrides = AgentRuntimeOverrides()

class AgentDefinition(AgentMetadata):
    instructions: str    # min_length=1, loaded from AGENT.md, not metadata.json
```

## 2. Implementation location

`backend/app/resources/specialists/<your_specialist_name>/`, containing exactly two
files: `metadata.json` and `AGENT.md`.

## 3. Registration / discovery

Fully filesystem-based, mirroring skills. `AgentRegistry`
(`backend/app/runtime/registry.py`) scans its specialists directory (default
`app/resources/specialists/`) at construction: each subdirectory must contain both files,
`metadata.json` parses into `AgentMetadata`, and `metadata.name` must equal the directory
name with no duplicates.

**Discovery also validates `allowed_tools` and `allowed_skills` against what's actually
registered**, when the registry is constructed with real `tool_registry`/`skill_registry`
references (as the app's composition root does):

```python
unknown = sorted(set(metadata.allowed_tools) - available_tools - _RUNTIME_TOOL_NAMES)
if unknown:
    self._invalid(metadata.name, f"unknown allowed tool(s): {', '.join(unknown)}")
```

An unknown tool or skill name raises `AgentDefinitionError` — *"Invalid definition for
agent 'your_specialist': unknown allowed tool(s): totally_fake_tool."* — at discovery
time, not silently at first use.

## 4. Security or capability requirements

None directly on the specialist itself — its capabilities are exactly the union of
`Capability` values its `allowed_tools` map to (see
[adding-a-tool.md](adding-a-tool.md)), granted via `SecurityPolicy.with_specialist()`.
This means:

- Every tool you list in `allowed_tools` **must** already have an entry in
  `_TOOL_CAPABILITIES` (`backend/app/security/permissions.py`), or the specialist can
  never actually use it despite passing discovery validation (discovery only checks the
  tool *exists* in the registry, not that it has a capability mapping).
- The four approval-gated capabilities (`FILESYSTEM_WRITE`, `COMMAND_EXECUTE`,
  `PYTHON_EXECUTE`, `ARTIFACT_CREATE`) still require human approval for a specialist —
  granting a tool doesn't bypass the gate.
- A specialist runs at `agent_depth=1` with delegation disabled — it cannot itself
  delegate to another specialist, regardless of what you put in its instructions.

## 5. Tests required

`backend/tests/unit/runtime/test_agent_registry.py` is the model to extend or match:
- A test asserting your specialist's `metadata.json` parses and discovers correctly
  (covered automatically the moment `AgentRegistry()` is constructed against the real
  resources directory anywhere in the suite).
- If you're testing a genuinely new failure mode, follow
  `test_unknown_allowed_tool_is_rejected`/`test_unknown_allowed_skill_is_rejected` (assert
  `AgentDefinitionError` with the expected message substring).
- An end-to-end test that actually delegates to the new specialist and checks its scoped
  `ToolRegistry`/`SkillRegistry` only contain what was granted — see
  `backend/tests/unit/runtime/test_delegation.py` / `test_parallel_delegation.py` for the
  pattern.

## 6. Documentation required

Add a row to the specialists table in
[tools-skills-and-specialists.md](../concepts/tools-skills-and-specialists.md) — name,
purpose, resource path, allowed tools, allowed skills, `max_iterations` override.

## 7. Common mistakes

- Listing a skill in `allowed_skills` that a tool in `allowed_tools` depends on
  conceptually but that the skill's own `recommended_tools` doesn't include — nothing
  enforces this pairing; check by hand.
- Forgetting that `runtime_overrides.max_iterations` is still capped by the parent's
  `max_subagent_iterations` (default 6) at child-construction time — setting it higher on
  the specialist alone has no effect if the parent's ceiling is lower.
- Granting a broad tool set "just in case" — every additional tool is one more approval
  gate or risk-classification surface the specialist can hit; the shipped `research`
  specialist deliberately has an empty `allowed_tools` rather than a defensive default.
- Writing `AGENT.md` instructions that assume delegation or web search work — as of today
  neither recursive delegation nor a working `web_search` tool exists (see
  [limitations.md](../reference/limitations.md)); don't write a specialist whose
  instructions depend on either.

## 8. Complete minimal example

`backend/app/resources/specialists/changelog_writer/metadata.json`:

```json
{
  "name": "changelog_writer",
  "description": "Summarizes a set of repository changes into a user-facing changelog entry.",
  "version": "1.0.0",
  "tags": ["writing", "repository"],
  "allowed_tools": ["get_changed_files", "git_inspect"],
  "allowed_skills": ["changelog_writing"],
  "runtime_overrides": {"max_iterations": 4}
}
```

`backend/app/resources/specialists/changelog_writer/AGENT.md`:

```markdown
# Changelog Writer Specialist

Given a delegated objective describing a set of changes, inspect them with
`get_changed_files`/`git_inspect`, then write a short, user-facing changelog entry per the
`changelog_writing` skill. Do not speculate about changes you have not inspected.
```

This assumes the `get_changed_files`/`git_inspect` tools already have `_TOOL_CAPABILITIES`
entries (they do — both map to `Capability.REPOSITORY_READ`) and that the
`changelog_writing` skill from [adding-a-skill.md](adding-a-skill.md) already exists. No
further registration code is needed — the next `AgentRegistry()` construction discovers
the new specialist automatically.
