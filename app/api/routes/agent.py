"""Thin HTTP interface for running the autonomous agent."""

from fastapi import APIRouter, Depends

from app.agent.runner import AgentRunner
from app.api.dependencies import get_agent_runner
from app.api.schemas.agent import AgentRunRequest, AgentRunResponse, ToolOutcomeSummary

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(
    request: AgentRunRequest,
    runner: AgentRunner = Depends(get_agent_runner),
) -> AgentRunResponse:
    """Run the runtime for one submitted goal."""

    state = await runner.run(request.goal)
    tool_observations = [
        observation
        for observation in state.observations
        if "tool_name" in observation.content.metadata
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
        stop_reason=state.stop_reason,
    )
