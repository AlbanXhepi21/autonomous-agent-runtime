"""Semantic tool-to-capability normalization owned by the runtime."""

from collections.abc import Mapping, Iterable
from typing import Any

from app.security.models import Capability, SecurityResource

_TOOL_CAPABILITIES = {
    "calculator": Capability.CALCULATOR_EVALUATE,
    "list_files": Capability.FILESYSTEM_READ,
    "read_file": Capability.FILESYSTEM_READ,
    "write_file": Capability.FILESYSTEM_WRITE,
    "run_command": Capability.COMMAND_EXECUTE,
    "python_exec": Capability.PYTHON_EXECUTE,
    "get_repository_tree": Capability.REPOSITORY_READ,
    "search_files": Capability.REPOSITORY_READ,
    "get_changed_files": Capability.REPOSITORY_READ,
    "git_inspect": Capability.REPOSITORY_READ,
    "register_artifact": Capability.ARTIFACT_CREATE,
    "web_search": Capability.WEB_SEARCH,
    "list_tables": Capability.DATABASE_SCHEMA_READ,
    "describe_table": Capability.DATABASE_SCHEMA_READ,
    "get_table_relationships": Capability.DATABASE_SCHEMA_READ,
    "search_schema": Capability.DATABASE_SCHEMA_READ,
}


def capability_for_tool(tool_name: str) -> Capability | None:
    return _TOOL_CAPABILITIES.get(tool_name)


def capabilities_for_tools(tool_names: Iterable[str]) -> frozenset[Capability]:
    return frozenset(
        capability for name in tool_names if (capability := capability_for_tool(name)) is not None
    )


def resource_for_tool(tool_name: str, arguments: Mapping[str, Any]) -> SecurityResource | None:
    """Produce a non-sensitive resource identity for future scoped rules."""

    if tool_name in {"list_files", "read_file", "write_file"}:
        return SecurityResource(resource_type="workspace_path", identifier=str(arguments.get("path", ".")))
    if tool_name == "run_command":
        return SecurityResource(resource_type="command", identifier=str(arguments.get("command", "")))
    if tool_name == "register_artifact":
        return SecurityResource(resource_type="workspace_artifact", identifier=str(arguments.get("source_path", "")))
    if tool_name in _TOOL_CAPABILITIES and _TOOL_CAPABILITIES[tool_name] == Capability.REPOSITORY_READ:
        return SecurityResource(resource_type="repository", identifier="workspace")
    if _TOOL_CAPABILITIES.get(tool_name) is Capability.DATABASE_SCHEMA_READ:
        names = arguments.get("table_names", arguments.get("table_name", ""))
        identifier = ",".join(names) if isinstance(names, list) else str(names)
        return SecurityResource(resource_type="database_schema", identifier=identifier or "configured_schema")
    return None
