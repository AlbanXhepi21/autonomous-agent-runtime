"""The documentation set describes real registries, contracts, and files.

Prose documentation cannot be type-checked, so it drifts silently unless
something keeps checking it against the code it describes. These tests are
that check: every relative link and referenced path must resolve, every
inventory table must match what the live registries actually contain, and no
document may carry a secret or a machine-specific path. None of this proves
the *prose* is well-written -- only that its concrete, checkable claims
(a link, a path, a name, a status) still agree with the repository.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.analytics.presentation.templates import ReportTemplateRegistry
from app.analytics.semantics.metrics import MetricRegistry
from app.composition.providers.tools import get_tool_registry
from app.config import Settings
from app.runtime.registry import AgentRegistry
from app.skills.registry import SkillRegistry
from tests.support import REPO_ROOT

DOCS_ROOT = REPO_ROOT / "docs"
ROOT_README = REPO_ROOT / "README.md"


def _all_doc_files() -> list[Path]:
    return [ROOT_README, *sorted(DOCS_ROOT.rglob("*.md"))]


def _strip_code_fences(text: str) -> list[tuple[str, bool]]:
    """Return (line, inside_fence) for every line, so headings inside a
    ```bash example (a shell comment starting with '#') are never mistaken
    for a Markdown heading."""

    lines = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        is_fence_marker = stripped.startswith("```")
        lines.append((line, in_fence))
        if is_fence_marker:
            in_fence = not in_fence
    return lines


def _headings(text: str) -> list[tuple[int, str]]:
    """Return (level, title) for every real heading, skipping fenced code."""

    headings = []
    for line, in_fence in _strip_code_fences(text):
        if in_fence:
            continue
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match:
            headings.append((len(match.group(1)), match.group(2).strip()))
    return headings


def _slugify(title: str) -> str:
    """Approximate GitHub's heading-anchor algorithm."""

    text = re.sub(r"`", "", title)
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text


_LINK_RE = re.compile(r"\]\(<([^>]+)>\)|\]\(([^)]+)\)")
_INLINE_PATH_RE = re.compile(r"`((?:backend|frontend)/[A-Za-z0-9_./-]+)`")


@dataclass(frozen=True)
class MarkdownLink:
    source_file: Path
    target: str


def _links_in(path: Path) -> list[MarkdownLink]:
    text = path.read_text(encoding="utf-8")
    links = []
    for line, in_fence in _strip_code_fences(text):
        if in_fence:
            continue
        for match in _LINK_RE.finditer(line):
            target = match.group(1) or match.group(2)
            links.append(MarkdownLink(source_file=path, target=target))
    return links


# ---------------------------------------------------------------------------
# 1 & 2: relative links resolve, and referenced repository paths exist.
# ---------------------------------------------------------------------------


def test_relative_markdown_links_resolve() -> None:
    heading_cache: dict[Path, set[str]] = {}
    failures = []

    for doc in _all_doc_files():
        for link in _links_in(doc):
            target = link.target
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            path_part, _, fragment = target.partition("#")

            if path_part:
                resolved = (doc.parent / path_part).resolve()
                if not resolved.exists():
                    failures.append(f"{doc.relative_to(REPO_ROOT)}: link target missing: {target}")
                    continue
            else:
                resolved = doc

            if fragment and resolved.suffix == ".md":
                if resolved not in heading_cache:
                    heading_cache[resolved] = {
                        _slugify(title) for _, title in _headings(resolved.read_text(encoding="utf-8"))
                    }
                if fragment not in heading_cache[resolved]:
                    failures.append(
                        f"{doc.relative_to(REPO_ROOT)}: anchor '#{fragment}' not found in "
                        f"{resolved.relative_to(REPO_ROOT)}"
                    )

    assert not failures, "Broken documentation links:\n" + "\n".join(failures)


#: The "adding a ..." guides each end with a "complete minimal example" using a
#: made-up name for a file that does not exist and is never created -- that's
#: the point of the example. These prefixes are the only paths this check
#: should not expect to find on disk.
KNOWN_ILLUSTRATIVE_EXAMPLE_PATHS = (
    "backend/app/resources/skills/changelog_writing/",
    "backend/app/resources/specialists/changelog_writer/",
    "backend/app/resources/report_templates/quick_summary/",
)


def test_referenced_repository_paths_exist() -> None:
    """Catches a path named in backtick-quoted prose (not just a Markdown
    link) that no longer exists, e.g. after a rename."""

    failures = []
    for doc in _all_doc_files():
        text = doc.read_text(encoding="utf-8")
        for line, in_fence in _strip_code_fences(text):
            if in_fence:
                continue
            for match in _INLINE_PATH_RE.finditer(line):
                candidate = match.group(1)
                if candidate.startswith(KNOWN_ILLUSTRATIVE_EXAMPLE_PATHS):
                    continue
                if not (REPO_ROOT / candidate).exists():
                    failures.append(f"{doc.relative_to(REPO_ROOT)}: referenced path does not exist: {candidate}")

    assert not failures, "Documentation references paths that do not exist:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------
# 3: no documentation file is empty.
# ---------------------------------------------------------------------------


def test_no_documentation_file_is_empty() -> None:
    failures = [
        str(doc.relative_to(REPO_ROOT))
        for doc in _all_doc_files()
        if len(doc.read_text(encoding="utf-8").strip()) < 40
    ]
    assert not failures, "Empty or near-empty documentation files:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------
# 4: top-level titles are not accidentally duplicated.
# ---------------------------------------------------------------------------


def test_top_level_titles_are_not_duplicated() -> None:
    titles: dict[str, list[Path]] = {}
    missing_title = []

    for doc in _all_doc_files():
        headings = _headings(doc.read_text(encoding="utf-8"))
        top_level = [title for level, title in headings if level == 1]
        if not top_level:
            missing_title.append(str(doc.relative_to(REPO_ROOT)))
            continue
        titles.setdefault(top_level[0], []).append(doc)

    assert not missing_title, "Documentation files with no top-level (#) title:\n" + "\n".join(missing_title)

    duplicates = {title: paths for title, paths in titles.items() if len(paths) > 1}
    assert not duplicates, "Duplicated top-level titles:\n" + "\n".join(
        f"{title!r}: {[str(p.relative_to(REPO_ROOT)) for p in paths]}" for title, paths in duplicates.items()
    )


# ---------------------------------------------------------------------------
# 5 & 6: Markdown and Mermaid code fences are balanced.
# ---------------------------------------------------------------------------


def test_code_fences_are_balanced() -> None:
    failures = []
    for doc in _all_doc_files():
        fence_lines = [line for line in doc.read_text(encoding="utf-8").splitlines() if line.strip().startswith("```")]
        if len(fence_lines) % 2 != 0:
            failures.append(f"{doc.relative_to(REPO_ROOT)}: odd number of ``` fence markers ({len(fence_lines)})")
    assert not failures, "Unbalanced code fences:\n" + "\n".join(failures)


def test_mermaid_fences_are_balanced() -> None:
    failures = []
    for doc in _all_doc_files():
        in_fence = False
        in_mermaid = False
        for line in doc.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped.startswith("```"):
                continue
            if not in_fence:
                in_fence = True
                in_mermaid = stripped[3:].strip().lower() == "mermaid"
            else:
                in_fence = False
                in_mermaid = False
        if in_fence:
            failures.append(f"{doc.relative_to(REPO_ROOT)}: a code fence (mermaid or otherwise) is never closed")
        if in_mermaid:
            failures.append(f"{doc.relative_to(REPO_ROOT)}: a ```mermaid fence is never closed")
    assert not failures, "Unbalanced mermaid fences:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------
# 7: environment-variable documentation matches Settings.
# ---------------------------------------------------------------------------

_ENV_VAR_ROW = re.compile(r"^\|\s*`([A-Z][A-Z0-9_]*)`")

#: Real, working environment variables that are deliberately not `Settings`
#: fields -- see docs/getting-started/configuration.md for why each exists
#: outside the pydantic-settings loader.
DOCUMENTED_NON_SETTINGS_VARS = {
    "SMTP_PASSWORD",  # read directly from os.environ by EnvironmentCredentialProvider
    "GITHUB_TOKEN",  # same
    "TEST_DATABASE_URL",  # test-only, never read by the application itself
    "NEXT_PUBLIC_API_BASE_URL",  # frontend, not a backend Settings field
}


def _documented_env_vars(doc: Path) -> set[str]:
    return {
        match.group(1)
        for line in doc.read_text(encoding="utf-8").splitlines()
        if (match := _ENV_VAR_ROW.match(line))
    }


def test_environment_variable_documentation_matches_settings() -> None:
    settings_vars = {name.upper() for name in Settings.model_fields}

    for doc_name in ("getting-started/configuration.md", "reference/environment-variables.md"):
        doc = DOCS_ROOT / doc_name
        documented = _documented_env_vars(doc)

        missing = settings_vars - documented
        assert not missing, f"{doc_name} is missing documented Settings field(s): {sorted(missing)}"

        unexpected = documented - settings_vars - DOCUMENTED_NON_SETTINGS_VARS
        assert not unexpected, (
            f"{doc_name} documents variable(s) that are neither a Settings field nor a known "
            f"exception in DOCUMENTED_NON_SETTINGS_VARS: {sorted(unexpected)}"
        )


# ---------------------------------------------------------------------------
# 8, 9, 10: tool / skill / specialist inventories match the live registries.
# ---------------------------------------------------------------------------


def _documented_code_span_names(doc: Path, section_title: str) -> set[str]:
    """Collect every `snake_case_name` code span appearing under the heading
    whose text starts with section_title, up to the next same-or-higher-level
    heading."""

    names: set[str] = set()
    in_section = False
    section_level: int | None = None
    for line in doc.read_text(encoding="utf-8").splitlines():
        heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2)
            if title.lower().startswith(section_title.lower()):
                in_section = True
                section_level = level
                continue
            if in_section and level <= (section_level or 0):
                in_section = False
            continue
        if in_section:
            names.update(re.findall(r"`([a-z][a-z0-9_]*)`", line))
    return names


def test_tool_inventory_matches_registered_tools() -> None:
    registry = get_tool_registry()
    registered = {str(definition["name"]) for definition in registry.definitions()}

    doc = DOCS_ROOT / "concepts" / "tools-skills-and-specialists.md"
    documented = _documented_code_span_names(doc, "Tools")

    missing = registered - documented
    assert not missing, f"tools-skills-and-specialists.md does not document tool(s): {sorted(missing)}"


def test_skill_inventory_matches_discovered_skills() -> None:
    registered = {skill.name for skill in SkillRegistry().list_skills()}

    doc = DOCS_ROOT / "concepts" / "tools-skills-and-specialists.md"
    documented = _documented_code_span_names(doc, "Skills")

    missing = registered - documented
    assert not missing, f"tools-skills-and-specialists.md does not document skill(s): {sorted(missing)}"


def test_specialist_inventory_matches_registered_specialists() -> None:
    registered = {agent.name for agent in AgentRegistry().list_agents()}

    doc = DOCS_ROOT / "concepts" / "tools-skills-and-specialists.md"
    documented = _documented_code_span_names(doc, "Specialists")

    missing = registered - documented
    assert not missing, f"tools-skills-and-specialists.md does not document specialist(s): {sorted(missing)}"


# ---------------------------------------------------------------------------
# 11: metric statuses match the canonical registry.
# ---------------------------------------------------------------------------

_METRIC_ROW = re.compile(r"^\|\s*`([a-z_]+:v\d+)`\s*\|[^|]*\|\s*([a-z_]+)\s*\|")


def test_metric_statuses_match_canonical_definitions() -> None:
    registry = MetricRegistry()
    canonical = {metric.identifier: metric.status for metric in registry.list_metrics()}

    doc = DOCS_ROOT / "concepts" / "semantic-metrics.md"
    text = doc.read_text(encoding="utf-8")
    documented = {match.group(1): match.group(2) for line in text.splitlines() if (match := _METRIC_ROW.match(line))}

    assert documented, f"No metric rows parsed from {doc.relative_to(REPO_ROOT)} -- table format may have changed"

    missing = set(canonical) - set(documented)
    assert not missing, f"semantic-metrics.md is missing metric(s): {sorted(missing)}"

    mismatched = {
        identifier: (canonical[identifier], documented[identifier])
        for identifier in documented
        if identifier in canonical and canonical[identifier] != documented[identifier]
    }
    assert not mismatched, f"semantic-metrics.md has stale status(es) (registry, documented): {mismatched}"


# ---------------------------------------------------------------------------
# 12: report-template inventory matches template resources.
# ---------------------------------------------------------------------------


def test_report_template_inventory_matches_resources() -> None:
    registered = {template.name for template in ReportTemplateRegistry().list_templates()}

    doc = DOCS_ROOT / "concepts" / "report-templates.md"
    documented = set(re.findall(r"^## `([a-z_]+)`", doc.read_text(encoding="utf-8"), flags=re.MULTILINE))

    assert documented == registered, (
        f"report-templates.md template headings {sorted(documented)} do not match the registry "
        f"{sorted(registered)}"
    )


# ---------------------------------------------------------------------------
# 13: no secrets or local absolute paths.
# ---------------------------------------------------------------------------

_SECRET_PATTERNS = [
    re.compile(r"/Users/[A-Za-z0-9_.-]+"),
    re.compile(r"/home/[A-Za-z0-9_.-]+"),
    re.compile(r"C:\\\\Users\\\\"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]

#: A connection string's user:password portion, checked separately from
#: _SECRET_PATTERNS because "is this a real credential" depends on the
#: captured text itself, not just where it appears.
_CREDENTIAL_IN_URL = re.compile(r"://(?P<user>[^\s/:]+):(?P<password>[^\s@/]+)@")
_PLACEHOLDER_CREDENTIAL = re.compile(r"^(<[^>]+>|user|pass|password|analytics_reader)$", re.IGNORECASE)


def test_no_secrets_or_local_paths_in_documentation() -> None:
    failures = []
    for doc in _all_doc_files():
        text = doc.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for pattern in _SECRET_PATTERNS:
                for match in pattern.finditer(line):
                    failures.append(f"{doc.relative_to(REPO_ROOT)}:{line_no}: matched {pattern.pattern!r}: {match.group(0)!r}")

            for match in _CREDENTIAL_IN_URL.finditer(line):
                user, password = match.group("user"), match.group("password")
                if _PLACEHOLDER_CREDENTIAL.match(user) and _PLACEHOLDER_CREDENTIAL.match(password):
                    continue
                failures.append(f"{doc.relative_to(REPO_ROOT)}:{line_no}: possible real credential in URL: {match.group(0)!r}")

    assert not failures, "Possible secret or machine-specific path in documentation:\n" + "\n".join(failures)
