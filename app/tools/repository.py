"""Thin repository-inspection tools over the controlled Repository abstraction."""

from typing import Any

from app.environment.repository import Repository, RepositoryError
from app.tools.base import Tool, ToolInputError


class _RepositoryTool(Tool):
    operation_kind = "repository"

    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    @staticmethod
    def _error(error: RepositoryError) -> ToolInputError:
        return ToolInputError(str(error))


class GetRepositoryTreeTool(_RepositoryTool):
    @property
    def name(self) -> str: return "get_repository_tree"
    @property
    def description(self) -> str: return "Show a bounded, source-oriented tree of the current repository."
    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"max_depth": {"type": "integer"}, "max_entries": {"type": "integer"}}, "required": [], "additionalProperties": False}
    async def execute(self, **arguments: Any) -> list[dict[str, str]]:
        try: return self._repository.tree(**arguments)
        except RepositoryError as error: raise self._error(error) from error


class SearchFilesTool(_RepositoryTool):
    @property
    def name(self) -> str: return "search_files"
    @property
    def description(self) -> str: return "Search repository paths and text with bounded results and ignored generated directories."
    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"path_query": {"type": "string"}, "text_query": {"type": "string"}, "max_results": {"type": "integer"}}, "required": [], "additionalProperties": False}
    async def execute(self, **arguments: Any) -> list[dict[str, object]]:
        try: return self._repository.search(**arguments)
        except RepositoryError as error: raise self._error(error) from error


class GetChangedFilesTool(_RepositoryTool):
    @property
    def name(self) -> str: return "get_changed_files"
    @property
    def description(self) -> str: return "List files modified through controlled workspace writes during this runtime instance."
    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
    async def execute(self, **arguments: Any) -> list[str]: return self._repository.changed_files()


class GitInspectTool(_RepositoryTool):
    @property
    def name(self) -> str: return "git_inspect"
    @property
    def description(self) -> str: return "Run one fixed read-only Git inspection: status, diff summary, or recent log."
    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"operation": {"type": "string"}}, "required": ["operation"], "additionalProperties": False}
    async def execute(self, **arguments: Any) -> dict[str, object]:
        try: return await self._repository.git_inspect(arguments["operation"])
        except RepositoryError as error: raise self._error(error) from error
