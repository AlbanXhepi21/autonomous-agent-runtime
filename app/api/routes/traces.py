"""Read-only access to process-local execution traces."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_trace_recorder
from app.observability import RunTrace, TraceRecorder

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}/trace", response_model=RunTrace)
async def get_run_trace(run_id: str, recorder: TraceRecorder = Depends(get_trace_recorder)) -> RunTrace:
    """Return a sanitized trace; V7.1 traces are only retained until process restart."""

    trace = recorder.get_trace(run_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Run trace not found.")
    return trace
