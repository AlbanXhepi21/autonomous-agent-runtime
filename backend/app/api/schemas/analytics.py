"""Stable, frontend-facing contracts for the Data Analyst Workbench."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.orchestration.views import (
    PublicRunEvent,
    PublicRunEventListResponse,
    RunHistoryResponse,
    RunMetricsResponse,
    RunResponse,
)

# Re-exported so route modules name one source for request and response shapes.
__all__ = [
    "ConversationCreateRequest", "ConversationDetailResponse", "ConversationListResponse",
    "ConversationResponse", "ConversationTitleRequest", "CreateRunRequest",
    "CreateRunResponse", "MessageResponse", "PublicRunEvent",
    "PublicRunEventListResponse", "RunHistoryResponse", "RunMetricsResponse", "RunResponse",
]


class CreateRunRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=200)


class CreateRunResponse(BaseModel):
    run_id: str
    conversation_id: str
    status: Literal["running"]


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=255)


class ConversationTitleRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class MessageResponse(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    run_id: str | None = None


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int
    limit: int
    offset: int


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse]
    messages_total: int
    messages_limit: int
    messages_offset: int
    runs: list["RunHistoryResponse"] = Field(default_factory=list)
