"""Small workspace-scoped filesystem tools."""

from typing import Any

from app.environment.workspace import Workspace, WorkspaceError
from app.tools.base import Tool, ToolInputError


class _WorkspaceTool(Tool):
    """Common marker and error conversion for workspace-backed tools."""

    operation_kind = "filesystem"

    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace

    @staticmethod
    def _input_error(error: WorkspaceError) -> ToolInputError:
        return ToolInputError(str(error))


class ListFilesTool(_WorkspaceTool):
    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return "List files and directories from the current workspace."

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative workspace directory."},
                "recursive": {"type": "boolean", "description": "Whether to include nested entries."},
            },
            "required": [],
            "additionalProperties": False,
        }

    async def execute(self, **arguments: Any) -> list[str]:
        try:
            return self._workspace.list_files(
                arguments.get("path", "."), recursive=arguments.get("recursive", False)
            )
        except WorkspaceError as error:
            raise self._input_error(error) from error


class ReadFileTool(_WorkspaceTool):
    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read a text file from the current workspace."

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Relative workspace file."}},
            "required": ["path"],
            "additionalProperties": False,
        }

    async def execute(self, **arguments: Any) -> str:
        try:
            return self._workspace.read_text(arguments["path"])
        except WorkspaceError as error:
            raise self._input_error(error) from error


class WriteFileTool(_WorkspaceTool):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write a text file inside the current workspace."

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative workspace file."},
                "content": {"type": "string", "description": "Text content to write."},
                "create_parents": {"type": "boolean", "description": "Create missing parent directories."},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        }

    async def execute(self, **arguments: Any) -> dict[str, str]:
        try:
            self._workspace.write_text(
                arguments["path"], arguments["content"],
                create_parents=arguments.get("create_parents", False),
            )
        except WorkspaceError as error:
            raise self._input_error(error) from error
        return {"path": arguments["path"], "status": "written"}
