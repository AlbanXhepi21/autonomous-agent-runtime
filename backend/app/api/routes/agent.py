"""Thin HTTP interface for running the autonomous agent."""

from fastapi import APIRouter, Depends, HTTPException

from app.analytics.semantics.datasets import AnalyticsDatasetStore
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
from app.tools.contracts import ToolResult

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(
    request: AgentRunRequest,
    runner: AgentRunner = Depends(get_agent_runner),
    service: DataSourceOnboardingService = Depends(get_data_source_onboarding_service),
    store: DataSourceStore = Depends(get_data_source_store),
    datasets: AnalyticsDatasetStore = Depends(get_analytics_dataset_store),
) -> AgentRunResponse:
    """Run the runtime for one submitted goal.

    When ``request.workspace_id`` is set, ``runner`` is rebuilt with its
    analytics tools scoped to that workspace's one active data source instead
    of the demo database; everything else about the run (LLM client, limits,
    memory, security policy) stays the same as the injected default. Omitted,
    ``runner`` is used exactly as provided -- unchanged from before this
    existed, including for callers (tests) that build and pass their own.
    """

    runtime = None
    if request.workspace_id is not None:
        try:
            analytics_tools, runtime = await resolve_workspace_tools(
                workspace_id=request.workspace_id, service=service, store=store, datasets=datasets,
            )
        except DataSourceOnboardingError as error:
            raise HTTPException(
                status_code=400, detail={"code": "no_active_data_source", "message": str(error)},
            ) from error
        runner = build_agent_runner(analytics_tools)

    try:
        state = await runner.run(request.goal, session_id=request.session_id)
    finally:
        if runtime is not None:
            await runtime.database.dispose()
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
