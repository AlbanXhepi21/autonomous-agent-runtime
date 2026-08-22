"""Filesystem discovery and progressive loading for specialist agent definitions."""

import json
import logging
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app.contracts.specialists import AgentDefinition, AgentMetadata
from app.core.exceptions import AgentDefinitionError, UnknownAgentError
from app.core.logging import log_event
from app.skills.registry import SkillRegistry
from app.tools.registry import ToolRegistry

# Definitions are discovered independently from any particular test or embedded
# runtime registry.  Keep validation strict for unknown names while allowing the
# runtime's built-in optional integrations to be absent from a narrowed registry.
_RUNTIME_TOOL_NAMES = frozenset({
    "calculator", "list_files", "read_file", "write_file", "run_command", "python_exec",
    "get_repository_tree", "search_files", "get_changed_files", "git_inspect",
    "register_artifact", "web_search", "list_tables", "describe_table",
    "get_table_relationships", "search_schema",
    "query_database",
    "analyze_dataset",
    "generate_report",
    "create_chart",
    "list_metrics", "describe_metric",
})


@dataclass(frozen=True, slots=True)
class _DiscoveredAgent:
    """Compact metadata plus instructions that have not yet been read."""

    metadata: AgentMetadata
    instructions_path: Path


class AgentRegistry:
    """Discover, validate, and load specialist definitions without executing them."""

    def __init__(
        self,
        agents_directory: Path | None = None,
        *,
        tool_registry: ToolRegistry | None = None,
        skill_registry: SkillRegistry | None = None,
    ) -> None:
        self._agents_directory = agents_directory or Path(__file__).parent.parent / "agents"
        self._tool_registry = tool_registry
        self._skill_registry = skill_registry
        self._logger = logging.getLogger(__name__)
        self._agents = self._discover()
        self._loaded_definitions: dict[str, AgentDefinition] = {}
        log_event(
            self._logger,
            logging.INFO,
            "agent_registry_initialized",
            agent_count=len(self._agents),
        )

    def list_agents(
        self, *, exclude_names: Collection[str] = ()
    ) -> list[AgentMetadata]:
        """Return compact metadata without reading specialist instructions."""

        excluded = set(exclude_names)
        return [
            agent.metadata
            for name, agent in sorted(self._agents.items())
            if name not in excluded
        ]

    def get_metadata(self, name: str) -> AgentMetadata:
        """Return compact discovery metadata for one specialist."""

        return self._get_agent(name).metadata

    def load_agent(self, name: str) -> AgentDefinition:
        """Read and cache one full specialist definition on demand."""

        if name not in self._loaded_definitions:
            agent = self._get_agent(name)
            try:
                instructions = agent.instructions_path.read_text(encoding="utf-8")
            except OSError as error:
                self._invalid(name, "could not read AGENT.md", error)
            try:
                definition_data = agent.metadata.model_dump()
                # A deliberately narrowed registry (used by embedded runtimes and
                # tests) cannot grant an integration it did not register.  The full
                # application registry contains all of these built-ins.
                if self._tool_registry is not None:
                    available_tools = {item["name"] for item in self._tool_registry.definitions()}
                    definition_data["allowed_tools"] = [
                        tool for tool in agent.metadata.allowed_tools if tool in available_tools
                    ]
                self._loaded_definitions[name] = AgentDefinition(
                    **definition_data, instructions=instructions
                )
            except ValidationError as error:
                self._invalid(name, "AGENT.md must contain instructions", error)
            log_event(self._logger, logging.INFO, "agent_definition_loaded", agent=name)
        return self._loaded_definitions[name]

    def _get_agent(self, name: str) -> _DiscoveredAgent:
        try:
            return self._agents[name]
        except KeyError as error:
            raise UnknownAgentError(f"Unknown agent: {name}") from error

    def _discover(self) -> dict[str, _DiscoveredAgent]:
        if not self._agents_directory.is_dir():
            self._invalid(self._agents_directory.name, "agents directory does not exist")
        discovered: dict[str, _DiscoveredAgent] = {}
        for directory in sorted(self._agents_directory.iterdir()):
            if not directory.is_dir():
                continue
            metadata_path = directory / "metadata.json"
            instructions_path = directory / "AGENT.md"
            if not metadata_path.exists() and not instructions_path.exists():
                continue
            if not metadata_path.is_file() or not instructions_path.is_file():
                self._invalid(directory.name, "directory must contain metadata.json and AGENT.md")
            metadata = self._read_metadata(metadata_path, directory.name)
            if metadata.name in discovered:
                self._invalid(metadata.name, "duplicate agent name")
            if metadata.name != directory.name:
                self._invalid(directory.name, "metadata name must match its directory")
            self._validate_capabilities(metadata)
            discovered[metadata.name] = _DiscoveredAgent(metadata, instructions_path)
        return discovered

    def _validate_capabilities(self, metadata: AgentMetadata) -> None:
        if self._tool_registry is not None:
            available_tools = {item["name"] for item in self._tool_registry.definitions()}
            unknown = sorted(set(metadata.allowed_tools) - available_tools - _RUNTIME_TOOL_NAMES)
            if unknown:
                self._invalid(metadata.name, f"unknown allowed tool(s): {', '.join(unknown)}")
        if self._skill_registry is not None:
            available_skills = {item.name for item in self._skill_registry.list_skills()}
            unknown = sorted(set(metadata.allowed_skills) - available_skills)
            if unknown:
                self._invalid(metadata.name, f"unknown allowed skill(s): {', '.join(unknown)}")

    def _read_metadata(self, path: Path, directory_name: str) -> AgentMetadata:
        try:
            raw_metadata = json.loads(path.read_text(encoding="utf-8"))
            return AgentMetadata.model_validate(raw_metadata)
        except (OSError, json.JSONDecodeError, ValidationError) as error:
            self._invalid(directory_name, "invalid metadata", error)

    def _invalid(self, name: str, detail: str, error: Exception | None = None) -> None:
        log_event(self._logger, logging.WARNING, "agent_definition_invalid", agent=name, detail=detail)
        raise AgentDefinitionError(f"Invalid definition for agent '{name}': {detail}.") from error
