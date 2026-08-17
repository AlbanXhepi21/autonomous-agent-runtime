"""Filesystem discovery and progressive loading for local skills."""

import json
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app.core.exceptions import SkillMetadataError, UnknownSkillError
from app.skills.models import SkillMetadata


@dataclass(frozen=True, slots=True)
class _DiscoveredSkill:
    """Metadata plus the path to instructions that have not yet been read."""

    metadata: SkillMetadata
    instructions_path: Path


class SkillRegistry:
    """Discover compact skill metadata and load instructions only on demand."""

    def __init__(self, skills_directory: Path | None = None) -> None:
        self._skills_directory = skills_directory or Path(__file__).parent
        self._skills = self._discover()
        self._loaded_instructions: dict[str, str] = {}

    def list_skills(
        self, *, exclude_names: Collection[str] = ()
    ) -> list[SkillMetadata]:
        """Return metadata without reading any full skill instructions."""

        excluded = set(exclude_names)
        return [
            skill.metadata
            for name, skill in sorted(self._skills.items())
            if name not in excluded
        ]

    def get_metadata(self, name: str) -> SkillMetadata:
        """Return compact metadata for a discovered skill."""

        return self._get_skill(name).metadata

    def load_skill(self, name: str) -> str:
        """Load and cache the full instructions for a known skill."""

        if name not in self._loaded_instructions:
            self._loaded_instructions[name] = self._get_skill(name).instructions_path.read_text(
                encoding="utf-8"
            )
        return self._loaded_instructions[name]

    def _get_skill(self, name: str) -> _DiscoveredSkill:
        try:
            return self._skills[name]
        except KeyError as error:
            raise UnknownSkillError(f"Unknown skill: {name}") from error

    def _discover(self) -> dict[str, _DiscoveredSkill]:
        discovered: dict[str, _DiscoveredSkill] = {}
        for directory in sorted(self._skills_directory.iterdir()):
            if not directory.is_dir():
                continue

            metadata_path = directory / "metadata.json"
            instructions_path = directory / "SKILL.md"
            if not metadata_path.exists() and not instructions_path.exists():
                continue
            if not metadata_path.is_file() or not instructions_path.is_file():
                raise SkillMetadataError(
                    f"Skill directory '{directory.name}' must contain metadata.json and SKILL.md."
                )

            metadata = self._read_metadata(metadata_path, directory.name)
            if metadata.name != directory.name:
                raise SkillMetadataError(
                    f"Skill metadata name '{metadata.name}' must match directory '{directory.name}'."
                )
            if metadata.name in discovered:
                raise SkillMetadataError(f"Duplicate skill name: {metadata.name}")
            discovered[metadata.name] = _DiscoveredSkill(metadata, instructions_path)
        return discovered

    @staticmethod
    def _read_metadata(path: Path, directory_name: str) -> SkillMetadata:
        try:
            raw_metadata = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SkillMetadataError(
                f"Invalid metadata for skill '{directory_name}'."
            ) from error

        try:
            return SkillMetadata.model_validate(raw_metadata)
        except ValidationError as error:
            raise SkillMetadataError(
                f"Invalid metadata for skill '{directory_name}'."
            ) from error
