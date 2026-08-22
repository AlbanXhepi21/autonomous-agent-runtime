"""Safe HTTP representations for human approval gates."""

from datetime import datetime
from pydantic import BaseModel

from app.security.approvals import ApprovalStatus
from app.security.contracts import Capability


class ApprovalResponse(BaseModel):
    id: str
    run_id: str
    parent_run_id: str | None
    agent_name: str
    capability: Capability
    tool_name: str
    resource: str | None
    argument_summary: dict[str, str | int | bool | None]
    reason: str
    status: ApprovalStatus
    created_at: datetime
    resolved_at: datetime | None
    expires_at: datetime | None
    policy_id: str
    action_fingerprint: str
