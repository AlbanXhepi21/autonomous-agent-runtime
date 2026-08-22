"""External human decision endpoints for persisted approval requests."""

import logging
from fastapi import APIRouter, Depends, HTTPException

from app.agent.runner import AgentRunner
from app.composition import get_agent_runner, get_run_manager, get_approval_store
from app.orchestration.run_manager import AgentRunManager
from app.api.schemas.approvals import ApprovalResponse
from app.core.logging import log_event
from app.security.approvals import ApprovalConflictError, ApprovalStatus, ApprovalStore

router = APIRouter(tags=["approvals"])
_logger = logging.getLogger(__name__)


def _response(request: object) -> ApprovalResponse:
    return ApprovalResponse.model_validate(request, from_attributes=True)


@router.get("/approvals/{approval_id}", response_model=ApprovalResponse)
async def get_approval(approval_id: str, store: ApprovalStore = Depends(get_approval_store)) -> ApprovalResponse:
    request = await store.get(approval_id)
    if request is None: raise HTTPException(404, "Approval request not found.")
    return _response(request)


@router.get("/runs/{run_id}/approvals", response_model=list[ApprovalResponse])
async def list_approvals(run_id: str, store: ApprovalStore = Depends(get_approval_store)) -> list[ApprovalResponse]:
    return [_response(item) for item in await store.list_for_run(run_id)]


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalResponse)
async def approve(approval_id: str, store: ApprovalStore = Depends(get_approval_store), runner: AgentRunner = Depends(get_agent_runner), manager: AgentRunManager = Depends(get_run_manager)) -> ApprovalResponse:
    try:
        request = await store.resolve(approval_id, ApprovalStatus.APPROVED)
    except KeyError: raise HTTPException(404, "Approval request not found.")
    except ApprovalConflictError: raise HTTPException(409, "Approval request is already resolved.")
    log_event(_logger, logging.INFO, "approval_approved", run_id=request.run_id, approval_id=request.id, agent=request.agent_name, capability=request.capability.value)
    resumed = await runner.resume_approval(approval_id)
    if resumed is not None: await manager.reconcile_resumed_run(resumed)
    return _response((await store.get(approval_id)) or request)


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalResponse)
async def reject(approval_id: str, store: ApprovalStore = Depends(get_approval_store), runner: AgentRunner = Depends(get_agent_runner), manager: AgentRunManager = Depends(get_run_manager)) -> ApprovalResponse:
    try:
        request = await store.resolve(approval_id, ApprovalStatus.REJECTED)
    except KeyError: raise HTTPException(404, "Approval request not found.")
    except ApprovalConflictError: raise HTTPException(409, "Approval request is already resolved.")
    log_event(_logger, logging.INFO, "approval_rejected", run_id=request.run_id, approval_id=request.id, agent=request.agent_name, capability=request.capability.value)
    resumed = await runner.resume_rejection(approval_id)
    if resumed is not None: await manager.reconcile_resumed_run(resumed)
    return _response((await store.get(approval_id)) or request)
