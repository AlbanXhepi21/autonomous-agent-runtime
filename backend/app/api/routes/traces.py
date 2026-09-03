"""Read-only access to process-local execution traces."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import require_permission
from app.composition import get_conversation_store, get_trace_recorder
from app.conversations.store import ConversationStore
from app.observability import RunTrace, TraceRecorder
from app.tenancy.context import TenantContext
from app.tenancy.permissions import Permission

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/runs", tags=["runs"])


@router.get("/{run_id}/trace", response_model=RunTrace)
async def get_run_trace(
    run_id: str,
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    recorder: TraceRecorder = Depends(get_trace_recorder),
    conversations: ConversationStore = Depends(get_conversation_store),
) -> RunTrace:
    """Return a sanitized trace; V7.1 traces are only retained until process restart.

    The trace store itself is process-local and has no tenant concept, so
    ownership is verified through the run's owning conversation first --
    the same "child resource, verified through its parent" pattern every
    other run-scoped lookup in this codebase uses.
    """

    if await conversations.get_run(workspace_id=context.workspace.id, run_id=run_id) is None:
        raise HTTPException(status_code=404, detail="Run trace not found.")
    trace = recorder.get_trace(run_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Run trace not found.")
    return trace
