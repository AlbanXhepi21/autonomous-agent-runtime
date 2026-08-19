"""Tests for filesystem-defined skills and progressive disclosure."""

import json
from pathlib import Path

import pytest

from app.agent.context import build_context
from app.agent.state import AgentState
from app.core.exceptions import SkillMetadataError, UnknownSkillError
from app.skills.registry import SkillRegistry
from app.tools.registry import ToolRegistry


def create_skill(
    skills_directory: Path,
    name: str,
    *,
    description: str = "A compact skill description.",
    instructions: str = "# Skill\n\nDetailed instructions.",
) -> Path:
    """Create a small filesystem skill fixture."""

    directory = skills_directory / name
    directory.mkdir()
    (directory / "metadata.json").write_text(
        json.dumps(
            {
                "name": name,
                "description": description,
                "version": "1.2.3",
                "tags": ["test"],
                "recommended_tools": ["calculator"],
            }
        ),
        encoding="utf-8",
    )
    instructions_path = directory / "SKILL.md"
    instructions_path.write_text(instructions, encoding="utf-8")
    return instructions_path


def test_skill_discovery_and_metadata_parsing() -> None:
    registry = SkillRegistry()

    research = registry.get_metadata("research")

    assert research.name == "research"
    assert research.description == "Plan evidence gathering, assess source quality, and produce qualified factual conclusions."
    assert research.version == "1.1.0"
    assert "verification" in research.tags
    assert [skill.name for skill in registry.list_skills()] == [
        "data_analysis",
        "research",
        "software_engineering",
    ]


def test_skill_loading_returns_full_instructions() -> None:
    registry = SkillRegistry()

    instructions = registry.load_skill("research")

    assert "Define the claim" in instructions
    assert "Cross-check important claims" in instructions


def test_unknown_skill_is_rejected() -> None:
    registry = SkillRegistry()

    with pytest.raises(UnknownSkillError, match="Unknown skill: absent"):
        registry.load_skill("absent")


def test_duplicate_loading_uses_cached_instructions(tmp_path: Path) -> None:
    instructions_path = create_skill(tmp_path, "cached", instructions="original instructions")
    registry = SkillRegistry(tmp_path)

    assert registry.load_skill("cached") == "original instructions"
    instructions_path.write_text("changed instructions", encoding="utf-8")

    assert registry.load_skill("cached") == "original instructions"


def test_initial_context_contains_metadata_but_not_skill_instructions() -> None:
    registry = SkillRegistry()
    state = AgentState(goal="Research a claim")

    context = build_context(state, ToolRegistry(), registry)

    research = next(skill for skill in context["available_skills"] if skill["name"] == "research")
    assert research["description"] == "Plan evidence gathering, assess source quality, and produce qualified factual conclusions."
    assert "Define the claim" not in json.dumps(context)
    assert context["loaded_skills"] == []


def test_loaded_skill_content_appears_only_after_loading() -> None:
    registry = SkillRegistry()
    state = AgentState(goal="Research a claim")
    state.loaded_skills["research"] = registry.load_skill("research")

    context = build_context(state, ToolRegistry(), registry)

    loaded_research = next(
        skill for skill in context["loaded_skills"] if skill["name"] == "research"
    )
    assert "Define the claim" in loaded_research["instructions"]
    assert "evidence ledger" in loaded_research["instructions"]
    assert "research" not in {skill["name"] for skill in context["available_skills"]}


def test_malformed_metadata_is_rejected(tmp_path: Path) -> None:
    directory = tmp_path / "broken"
    directory.mkdir()
    (directory / "metadata.json").write_text("{not json", encoding="utf-8")
    (directory / "SKILL.md").write_text("# Broken", encoding="utf-8")

    with pytest.raises(SkillMetadataError, match="Invalid metadata for skill 'broken'"):
        SkillRegistry(tmp_path)
