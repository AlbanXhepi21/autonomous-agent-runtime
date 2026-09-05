"""Thin HTTP interface for running the autonomous agent."""

from fastapi import APIRouter, Depends, HTTPException

from app.analytics.semantics.datasets import AnalyticsDatasetStore
from app.api.dependencies import require_csrf, require_permission
from app.api.schemas.agent import AgentRunRequest, AgentRunResponse, ToolOutcomeSummary
from app.composition import (
    build_agent_runner,
    get_agent_runner,
    get_analytics_dataset_store,
    get_data_source_onboarding_service,
    get_data_source_store,
)
from app.datasources.agent_integration import resolve_workspace_tools
from app.datasources.service import DataSourceOnboardingError, DataSourceOnboardingService
from app.datasources.store import DataSourceStore
from app.runtime.runner import AgentRunner
from app.tenancy.context import TenantContext
from app.tenancy.permissions import Permission
from app.tools.contracts import ToolResult

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/agent", tags=["agent"])


@router.post("/run", response_model=AgentRunResponse, dependencies=[Depends(require_csrf)])
async def run_agent(
    request: AgentRunRequest,
    context: TenantContext = Depends(require_permission(Permission.RUN_ANALYSES)),
    runner: AgentRunner = Depends(get_agent_runner),
    service: DataSourceOnboardingService = Depends(get_data_source_onboarding_service),
    store: DataSourceStore = Depends(get_data_source_store),
    datasets: AnalyticsDatasetStore = Depends(get_analytics_dataset_store),
) -> AgentRunResponse:
    """Run the runtime for one submitted goal, scoped to the caller's workspace.

    When the workspace has an active data source, the run's analytics tools
    are scoped to it instead of the built-in demo database; everything else
    about the run (LLM client, limits, memory, security policy) stays the
    same as the injected default. Without one, the demo database is used --
    unchanged capability from before tenant auth existed on this route, and
    a known, separately-tracked limitation (see docs/TENANCY.md). Memory and
    artifact registration during the run are always scoped to the
    authenticated workspace, regardless of which analytics tools are active.
    """

    workspace_id = context.workspace.id
    try:
        analytics_tools, _runtime = await resolve_workspace_tools(
            workspace_id=workspace_id, service=service, store=store, datasets=datasets,
        )
        runner = build_agent_runner(analytics_tools)
    except DataSourceOnboardingError:
        pass  # No active data source for this workspace -- fall back to the injected default runner.

    # The runtime returned above (when a workspace has an active data source)
    # is drawn from DataSourceOnboardingService's shared connection pool, not
    # built fresh for this run -- it must not be disposed here. The pool
    # keeps it alive for the next run against the same connection, and only
    # invalidates it itself on a configuration change, disable, or delete.
    state = await runner.run(request.goal, session_id=request.session_id, workspace_id=str(workspace_id))
    tool_observations = [
        observation
        for observation in state.observations
        if isinstance(observation.content, ToolResult)
        and "tool_name" in observation.content.metadata
    ]
    tool_outcomes = [
        ToolOutcomeSummary(
            tool_name=observation.source,
            success=observation.content.success,
            error=observation.content.error,
            blocked_as_duplicate=bool(
                observation.content.metadata.get("duplicate_action", False)
            ),
        )
        for observation in tool_observations
    ]
    tools_used = list(
        dict.fromkeys(
            outcome.tool_name for outcome in tool_outcomes if not outcome.blocked_as_duplicate
        )
    )
    return AgentRunResponse(
        final_answer=state.final_answer,
        run_id=state.run_id,
        iteration_count=state.iteration_count,
        tool_call_count=state.total_tool_calls,
        recoverable_error_count=state.recoverable_error_count,
        duplicate_action_count=sum(
            outcome.blocked_as_duplicate for outcome in tool_outcomes
        ),
        tools_used=tools_used,
        tool_outcomes=tool_outcomes,
        skills_used=list(state.loaded_skills),
        completed=state.completed,
        status=state.status,
        stop_reason=state.stop_reason,
        artifacts=state.artifacts,
    )
