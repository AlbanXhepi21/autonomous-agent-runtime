"""External human decision endpoints for persisted approval requests.

``ApprovalStore`` is a local-process file store keyed by ``run_id`` with no
tenant concept of its own (see docs/TENANCY.md) -- every route here verifies
ownership through the run's owning conversation first, the same
"child resource, verified through its parent" pattern ``traces.py`` uses.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import require_csrf, require_permission
from app.api.schemas.approvals import ApprovalResponse
from app.composition import get_agent_runner, get_approval_store, get_conversation_store, get_run_manager
from app.conversations.store import ConversationStore
from app.core.logging import log_event
from app.orchestration.run_manager import AgentRunManager
from app.runtime.runner import AgentRunner
from app.security.approvals import ApprovalConflictError, ApprovalStatus, ApprovalStore
from app.tenancy.context import TenantContext
from app.tenancy.permissions import Permission

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}", tags=["approvals"])
_logger = logging.getLogger(__name__)


def _response(request: object) -> ApprovalResponse:
    return ApprovalResponse.model_validate(request, from_attributes=True)


async def _require_owned_run(conversations: ConversationStore, *, workspace_id, run_id: str) -> None:
    if await conversations.get_run(workspace_id=workspace_id, run_id=run_id) is None:
        raise HTTPException(404, "Approval request not found.")


@router.get("/approvals/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: str,
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    store: ApprovalStore = Depends(get_approval_store),
    conversations: ConversationStore = Depends(get_conversation_store),
) -> ApprovalResponse:
    request = await store.get(approval_id)
    if request is None: raise HTTPException(404, "Approval request not found.")
    await _require_owned_run(conversations, workspace_id=context.workspace.id, run_id=request.run_id)
    return _response(request)


@router.get("/runs/{run_id}/approvals", response_model=list[ApprovalResponse])
async def list_approvals(
    run_id: str,
    context: TenantContext = Depends(require_permission(Permission.READ_TENANT_RESOURCES)),
    store: ApprovalStore = Depends(get_approval_store),
    conversations: ConversationStore = Depends(get_conversation_store),
) -> list[ApprovalResponse]:
    await _require_owned_run(conversations, workspace_id=context.workspace.id, run_id=run_id)
    return [_response(item) for item in await store.list_for_run(run_id)]


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalResponse, dependencies=[Depends(require_csrf)])
async def approve(
    approval_id: str,
    context: TenantContext = Depends(require_permission(Permission.RUN_ANALYSES)),
    store: ApprovalStore = Depends(get_approval_store), runner: AgentRunner = Depends(get_agent_runner),
    manager: AgentRunManager = Depends(get_run_manager), conversations: ConversationStore = Depends(get_conversation_store),
) -> ApprovalResponse:
    try:
        request = await store.get(approval_id)
        if request is None: raise HTTPException(404, "Approval request not found.")
        await _require_owned_run(conversations, workspace_id=context.workspace.id, run_id=request.run_id)
        request = await store.resolve(approval_id, ApprovalStatus.APPROVED)
    except KeyError: raise HTTPException(404, "Approval request not found.")
    except ApprovalConflictError: raise HTTPException(409, "Approval request is already resolved.")
    log_event(_logger, logging.INFO, "approval_approved", run_id=request.run_id, approval_id=request.id, agent=request.agent_name, capability=request.capability.value)
    resumed = await runner.resume_approval(approval_id)
    if resumed is not None: await manager.reconcile_resumed_run(resumed)
    return _response((await store.get(approval_id)) or request)


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalResponse, dependencies=[Depends(require_csrf)])
async def reject(
    approval_id: str,
    context: TenantContext = Depends(require_permission(Permission.RUN_ANALYSES)),
    store: ApprovalStore = Depends(get_approval_store), runner: AgentRunner = Depends(get_agent_runner),
    manager: AgentRunManager = Depends(get_run_manager), conversations: ConversationStore = Depends(get_conversation_store),
) -> ApprovalResponse:
    try:
        request = await store.get(approval_id)
        if request is None: raise HTTPException(404, "Approval request not found.")
        await _require_owned_run(conversations, workspace_id=context.workspace.id, run_id=request.run_id)
        request = await store.resolve(approval_id, ApprovalStatus.REJECTED)
    except KeyError: raise HTTPException(404, "Approval request not found.")
    except ApprovalConflictError: raise HTTPException(409, "Approval request is already resolved.")
    log_event(_logger, logging.INFO, "approval_rejected", run_id=request.run_id, approval_id=request.id, agent=request.agent_name, capability=request.capability.value)
    resumed = await runner.resume_rejection(approval_id)
    if resumed is not None: await manager.reconcile_resumed_run(resumed)
    return _response((await store.get(approval_id)) or request)
