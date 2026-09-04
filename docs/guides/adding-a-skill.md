# Adding a skill

## 1. Relevant contract

`SkillMetadata` (`backend/app/skills/contracts.py`, `extra="forbid"`):

```python
class SkillMetadata(BaseModel):
    name: str          # min_length=1, must equal the directory name
    description: str   # min_length=1
    version: str       # min_length=1
    tags: list[str] = []
    recommended_tools: list[str] = []
```

A skill has no executable code — its actual content is a Markdown file, `SKILL.md`, read
as plain text.

## 2. Implementation location

`backend/app/resources/skills/<your_skill_name>/`, containing exactly two files:
`metadata.json` and `SKILL.md`.

## 3. Registration / discovery

Fully filesystem-based — no code changes needed beyond the two files. `SkillRegistry`
(`backend/app/skills/registry.py`) scans its skills directory (default
`app/resources/skills/`) at construction time: every subdirectory must contain both
`metadata.json` and `SKILL.md`, `metadata.json` is parsed into `SkillMetadata`, and the
registry enforces `metadata.name == directory_name` and rejects duplicate names. `SKILL.md`
itself is read lazily, only when a run actually calls `load_skill` for that name.

## 4. Security or capability requirements

None. Skills carry no `Capability` and require no approval — they only ever load text
into context. A specialist's `allowed_skills` list (see
[adding-a-specialist.md](adding-a-specialist.md)) is validated against real registered
skill names at discovery time, so a specialist referencing a skill that doesn't exist (or
a name typo) fails fast with `AgentDefinitionError`, not silently.

## 5. Tests required

`backend/tests/unit/tools/test_skills.py` constructs `SkillRegistry()` pointed at the real
`app/resources/skills/` directory and asserts every shipped skill's `metadata.json` parses
— a broken new skill's `metadata.json` fails this test immediately (or fails at
collection/first-use of `SkillRegistry()` anywhere else in the suite). No further test is
required for the skill's own registration to be verified. If your skill's
`recommended_tools` list references tool names, there's no automated check that those
names exist (it's a hint, not a validated reference) — verify them by hand.

## 6. Documentation required

Add a row to the skills table in
[tools-skills-and-specialists.md](../concepts/tools-skills-and-specialists.md) — name,
purpose, resource path, version, tags, recommended tools.

## 7. Common mistakes

- `metadata.name` not matching the directory name exactly — the registry rejects this at
  discovery time for the whole registry, not just the one skill, since discovery happens
  eagerly at construction.
- Adding a field to `metadata.json` beyond `name`/`description`/`version`/`tags`/
  `recommended_tools` — the schema is `extra="forbid"`, so any unknown key rejects the
  entire file.
- Writing `SKILL.md` as a rigid step-by-step procedure rather than guidance. Every shipped
  skill's own text explicitly favors judgment over a fixed sequence (`data_analysis/SKILL.md`
  opens with exactly this framing) — the model still decides how to apply it.
- Listing `recommended_tools` that the target specialist doesn't actually have in its
  `allowed_tools` — nothing enforces this consistency; check by hand when pairing a skill
  with a specialist.

## 8. Complete minimal example

`backend/app/resources/skills/changelog_writing/metadata.json`:

```json
{
  "name": "changelog_writing",
  "description": "Summarize a set of changes into a short, user-facing changelog entry.",
  "version": "1.0.0",
  "tags": ["writing", "changelog"],
  "recommended_tools": ["get_changed_files", "git_inspect"]
}
```

`backend/app/resources/skills/changelog_writing/SKILL.md`:

```markdown
# Changelog Writing

Summarize what changed for the person reading a changelog, not for another engineer.

- Group changes by user-visible effect, not by file touched.
- One line per entry; lead with the verb (Added, Fixed, Changed, Removed).
- Omit internal refactors with no visible behavior change.
- If nothing changed that a user would notice, say so plainly rather than padding entries.
```

No registration code is needed — dropping these two files under
`backend/app/resources/skills/changelog_writing/` is sufficient; the next `SkillRegistry()`
construction discovers it automatically.
