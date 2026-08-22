"""Persistent, runtime-owned approval requests and resumable action checkpoints."""

import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.security.contracts import Capability, SecurityAction, SecuritySubject
from app.core.logging import log_event

_logger = logging.getLogger(__name__)


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalRequest(BaseModel):
    """Safe review record; exact executable arguments are stored separately."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    parent_run_id: str | None = None
    agent_name: str
    capability: Capability
    tool_name: str
    resource: str | None = None
    argument_summary: dict[str, str | int | bool | None] = Field(default_factory=dict)
    reason: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
    expires_at: datetime | None = None
    policy_id: str
    action_fingerprint: str
    execution_started_at: datetime | None = None
    execution_completed_at: datetime | None = None


class ApprovalCheckpoint(BaseModel):
    """Private resume data, intentionally absent from ApprovalRequest responses."""

    model_config = ConfigDict(extra="forbid")

    state: dict
    tool_name: str
    tool_arguments: dict
    action_fingerprint: str
    session_id: str | None = None


class ApprovalConflictError(ValueError):
    pass


def action_fingerprint(subject: SecuritySubject, action: SecurityAction, arguments: dict) -> str:
    payload = {
        "agent": subject.agent_name, "run_id": subject.run_id,
        "parent_run_id": subject.parent_run_id, "capability": action.capability.value if action.capability else None,
        "tool": action.tool_name, "resource": action.resource.model_dump(mode="json") if action.resource else None,
        "arguments": arguments,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def safe_argument_summary(arguments: dict) -> dict[str, str | int | bool | None]:
    summary: dict[str, str | int | bool | None] = {}
    for key, value in arguments.items():
        if key in {"content", "code"} and isinstance(value, str):
            summary[f"{key}_bytes"] = len(value.encode())
            summary[f"{key}_sha256"] = hashlib.sha256(value.encode()).hexdigest()
        elif key.lower() in {"password", "secret", "token", "api_key", "authorization"}:
            summary[key] = "[REDACTED]"
        elif isinstance(value, (str, int, bool)) or value is None:
            if isinstance(value, str):
                from app.core.logging import safe_log_value
                summary[key] = safe_log_value(value[:200])
            else:
                summary[key] = value
        elif isinstance(value, list):
            summary[f"{key}_count"] = len(value)
        else:
            summary[key] = "[structured value]"
    return summary


class ApprovalStore(ABC):
    @abstractmethod
    async def create(self, request: ApprovalRequest, checkpoint: ApprovalCheckpoint) -> ApprovalRequest: ...
    @abstractmethod
    async def get(self, approval_id: str) -> ApprovalRequest | None: ...
    @abstractmethod
    async def list_for_run(self, run_id: str) -> list[ApprovalRequest]: ...
    @abstractmethod
    async def resolve(self, approval_id: str, status: ApprovalStatus) -> ApprovalRequest: ...
    @abstractmethod
    async def claim_approved(self, approval_id: str) -> tuple[ApprovalRequest, ApprovalCheckpoint] | None: ...
    @abstractmethod
    async def claim_rejected(self, approval_id: str) -> tuple[ApprovalRequest, ApprovalCheckpoint] | None: ...
    @abstractmethod
    async def complete_execution(self, approval_id: str, state: dict) -> None: ...
    @abstractmethod
    async def checkpoint(self, approval_id: str) -> ApprovalCheckpoint | None: ...


class FileApprovalStore(ApprovalStore):
    """Atomic JSON persistence for approvals and private resume checkpoints."""

    def __init__(self, root: Path, *, ttl_seconds: int | None = None) -> None:
        self._root = root
        self._ttl = ttl_seconds
        self._lock = asyncio.Lock()

    async def create(self, request: ApprovalRequest, checkpoint: ApprovalCheckpoint) -> ApprovalRequest:
        async with self._lock:
            if self._ttl is not None and request.expires_at is None:
                request.expires_at = request.created_at + timedelta(seconds=self._ttl)
            self._write(request, checkpoint)
            return request.model_copy(deep=True)

    async def get(self, approval_id: str) -> ApprovalRequest | None:
        async with self._lock:
            item = self._read(approval_id)
            if item is None: return None
            request, checkpoint = item
            self._expire(request, checkpoint)
            return request.model_copy(deep=True)

    async def list_for_run(self, run_id: str) -> list[ApprovalRequest]:
        async with self._lock:
            results = []
            for path in self._root.glob("*.json"):
                if path.name.endswith(".checkpoint.json"): continue
                item = self._read(path.stem)
                if item and item[0].run_id == run_id:
                    self._expire(*item); results.append(item[0].model_copy(deep=True))
            return sorted(results, key=lambda value: value.created_at)

    async def resolve(self, approval_id: str, status: ApprovalStatus) -> ApprovalRequest:
        if status not in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}:
            raise ValueError("Only approval or rejection may resolve a request.")
        async with self._lock:
            item = self._read(approval_id)
            if item is None: raise KeyError(approval_id)
            request, checkpoint = item; self._expire(request, checkpoint)
            if request.status is status: return request.model_copy(deep=True)
            if request.status is not ApprovalStatus.PENDING:
                raise ApprovalConflictError("Approval request is already resolved.")
            request.status = status; request.resolved_at = datetime.now(timezone.utc)
            self._write(request, checkpoint)
            return request.model_copy(deep=True)

    async def claim_approved(self, approval_id: str) -> tuple[ApprovalRequest, ApprovalCheckpoint] | None:
        return await self._claim(approval_id, ApprovalStatus.APPROVED)

    async def claim_rejected(self, approval_id: str) -> tuple[ApprovalRequest, ApprovalCheckpoint] | None:
        return await self._claim(approval_id, ApprovalStatus.REJECTED)

    async def _claim(self, approval_id: str, expected: ApprovalStatus) -> tuple[ApprovalRequest, ApprovalCheckpoint] | None:
        async with self._lock:
            item = self._read(approval_id)
            if item is None: raise KeyError(approval_id)
            request, checkpoint = item; self._expire(request, checkpoint)
            if request.status is not expected or request.execution_started_at is not None:
                return None
            request.execution_started_at = datetime.now(timezone.utc); self._write(request, checkpoint)
            return request.model_copy(deep=True), checkpoint.model_copy(deep=True)

    async def complete_execution(self, approval_id: str, state: dict) -> None:
        async with self._lock:
            item = self._read(approval_id)
            if item is None: raise KeyError(approval_id)
            request, checkpoint = item
            checkpoint.state = state; request.execution_completed_at = datetime.now(timezone.utc)
            self._write(request, checkpoint)

    async def checkpoint(self, approval_id: str) -> ApprovalCheckpoint | None:
        async with self._lock:
            item = self._read(approval_id)
            return item[1].model_copy(deep=True) if item else None

    def _expire(self, request: ApprovalRequest, checkpoint: ApprovalCheckpoint) -> None:
        if request.status is ApprovalStatus.PENDING and request.expires_at and request.expires_at <= datetime.now(timezone.utc):
            request.status = ApprovalStatus.EXPIRED; request.resolved_at = datetime.now(timezone.utc); self._write(request, checkpoint)
            log_event(_logger, logging.INFO, "approval_expired", run_id=request.run_id,
                      approval_id=request.id, agent=request.agent_name, capability=request.capability.value)

    def _read(self, approval_id: str) -> tuple[ApprovalRequest, ApprovalCheckpoint] | None:
        path = self._root / f"{approval_id}.json"; checkpoint_path = self._root / f"{approval_id}.checkpoint.json"
        if not path.is_file() or not checkpoint_path.is_file(): return None
        return ApprovalRequest.model_validate_json(path.read_text()), ApprovalCheckpoint.model_validate_json(checkpoint_path.read_text())

    def _write(self, request: ApprovalRequest, checkpoint: ApprovalCheckpoint) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        for path, data in ((self._root / f"{request.id}.json", request.model_dump_json()), (self._root / f"{request.id}.checkpoint.json", checkpoint.model_dump_json())):
            temporary = path.with_suffix(path.suffix + ".tmp"); temporary.write_text(data); temporary.replace(path)
