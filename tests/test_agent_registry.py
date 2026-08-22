"""Tests for filesystem-defined specialist agent discovery."""

import json
from pathlib import Path

import pytest

from app.runtime.context import ContextBuilder
from app.runtime.registry import AgentRegistry
from app.runtime.state import AgentState
from app.core.exceptions import AgentDefinitionError, UnknownAgentError
from app.core.limits import RuntimeLimits
from app.environment import CommandExecutor, PythonExecutor, Workspace
from app.environment.repository import Repository
from app.artifacts.store import WorkspaceArtifactStore
from app.skills.registry import SkillRegistry
from app.tools.calculator import CalculatorTool
from app.tools.commands import RunCommandTool
from app.tools.filesystem import ListFilesTool, ReadFileTool, WriteFileTool
from app.tools.python_exec import PythonExecTool
from app.tools.repository import GetChangedFilesTool, GetRepositoryTreeTool, GitInspectTool, SearchFilesTool
from app.tools.artifacts import RegisterArtifactTool
from app.tools.registry import ToolRegistry


def valid_tools() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    workspace = Workspace(Path.cwd())
    registry.register(ListFilesTool(workspace))
    registry.register(ReadFileTool(workspace))
    registry.register(WriteFileTool(workspace))
    registry.register(RunCommandTool(CommandExecutor(workspace)))
    registry.register(PythonExecTool(PythonExecutor(workspace)))
    repository = Repository(workspace)
    registry.register(GetRepositoryTreeTool(repository))
    registry.register(SearchFilesTool(repository))
    registry.register(GetChangedFilesTool(repository))
    registry.register(GitInspectTool(repository))
    registry.register(RegisterArtifactTool(WorkspaceArtifactStore(workspace)))
    return registry


def create_agent(
    agents_directory: Path,
    directory_name: str,
    *,
    name: str | None = None,
    metadata: dict[str, object] | None = None,
    instructions: str = "# Specialist\n\nFull private instructions.",
) -> None:
    directory = agents_directory / directory_name
    directory.mkdir()
    payload = {
        "name": name or directory_name,
        "description": "A compact specialist description.",
        "version": "1.0.0",
        "tags": ["test"],
        "allowed_tools": [],
        "allowed_skills": [],
        "runtime_overrides": {},
    }
    if metadata:
        payload.update(metadata)
    (directory / "metadata.json").write_text(json.dumps(payload), encoding="utf-8")
    (directory / "AGENT.md").write_text(instructions, encoding="utf-8")


def test_agent_discovery_and_compact_metadata() -> None:
    registry = AgentRegistry(tool_registry=valid_tools(), skill_registry=SkillRegistry())

    assert [agent.name for agent in registry.list_agents()] == [
        "data_analyst", "research", "software_engineer"
    ]
    research = registry.get_metadata("research")
    assert research.description == "Investigates external factual questions and collects evidence."
    assert research.allowed_skills == ["research"]
    assert not hasattr(research, "instructions")


def test_full_definition_is_loaded_only_on_demand() -> None:
    registry = AgentRegistry()

    definition = registry.load_agent("research")

    assert definition.name == "research"
    assert "Define the claim" in definition.instructions


def test_unknown_agent_is_rejected() -> None:
    with pytest.raises(UnknownAgentError, match="Unknown agent: absent"):
        AgentRegistry().load_agent("absent")


def test_malformed_metadata_is_rejected(tmp_path: Path) -> None:
    directory = tmp_path / "broken"
    directory.mkdir()
    (directory / "metadata.json").write_text("{not json", encoding="utf-8")
    (directory / "AGENT.md").write_text("# Broken", encoding="utf-8")

    with pytest.raises(AgentDefinitionError, match="Invalid definition for agent 'broken'"):
        AgentRegistry(tmp_path)


def test_duplicate_agent_names_are_rejected(tmp_path: Path) -> None:
    create_agent(tmp_path, "shared")
    create_agent(tmp_path, "zsecond", name="shared")

    with pytest.raises(AgentDefinitionError, match="duplicate agent name"):
        AgentRegistry(tmp_path)


def test_unknown_allowed_tool_is_rejected(tmp_path: Path) -> None:
    create_agent(tmp_path, "broken", metadata={"allowed_tools": ["nonexistent_tool"]})

    with pytest.raises(AgentDefinitionError, match="unknown allowed tool"):
        AgentRegistry(tmp_path, tool_registry=valid_tools())


def test_unknown_allowed_skill_is_rejected(tmp_path: Path) -> None:
    create_agent(tmp_path, "broken", metadata={"allowed_skills": ["nonexistent_skill"]})

    with pytest.raises(AgentDefinitionError, match="unknown allowed skill"):
        AgentRegistry(tmp_path, skill_registry=SkillRegistry())


def test_context_can_expose_compact_specialist_metadata_without_instructions() -> None:
    registry = AgentRegistry()
    context = ContextBuilder(
        valid_tools(), SkillRegistry(), RuntimeLimits(), agent_registry=registry
    ).build(AgentState(goal="Need a specialist"))

    research = next(agent for agent in context["available_specialist_agents"] if agent["name"] == "research")
    assert research["description"] == "Investigates external factual questions and collects evidence."
    assert "Define the claim" not in json.dumps(context)


def test_definition_is_independent_from_runtime_state() -> None:
    definition = AgentRegistry().load_agent("data_analyst")
    state = AgentState(goal="Analyze a metric")

    assert definition.instructions
    assert not hasattr(definition, "iteration_count")
    assert state.iteration_count == 0
