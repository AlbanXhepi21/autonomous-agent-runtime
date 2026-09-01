"""Conversation history API. It never exposes, clears, or mutates agent memory."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.analytics.presentation.charts import ChartSpec
from app.api.schemas.analytics import (
    AnswerSource,
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationTitleRequest,
    MessageResponse,
    RunHistoryResponse,
    RunMetricsResponse,
)
from app.composition import get_conversation_store
from app.conversations.store import ConversationStore

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


def _conversation(record) -> ConversationResponse:
    return ConversationResponse(id=str(record.id), title=record.title, created_at=record.created_at, updated_at=record.updated_at)


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(request: ConversationCreateRequest, store: ConversationStore = Depends(get_conversation_store)) -> ConversationResponse:
    return _conversation(await store.create_conversation(request.title))


@router.get("", response_model=ConversationListResponse)
async def list_conversations(limit: int = Query(default=30, ge=1, le=100), offset: int = Query(default=0, ge=0), store: ConversationStore = Depends(get_conversation_store)) -> ConversationListResponse:
    items, total = await store.list_conversations(limit=limit, offset=offset)
    return ConversationListResponse(items=[_conversation(item) for item in items], total=total, limit=limit, offset=offset)


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: UUID, message_limit: int = Query(default=100, ge=1, le=200), message_offset: int = Query(default=0, ge=0), store: ConversationStore = Depends(get_conversation_store)) -> ConversationDetailResponse:
    conversation = await store.get_conversation(conversation_id)
    if conversation is None: raise HTTPException(status_code=404, detail={"code": "unknown_conversation", "message": "Conversation not found."})
    messages, total = await store.list_messages(conversation_id, limit=message_limit, offset=message_offset)
    runs = await store.list_runs(conversation_id)
    return ConversationDetailResponse(**_conversation(conversation).model_dump(), messages=[MessageResponse(id=str(message.id), role=message.role, content=message.content, created_at=message.created_at, run_id=message.run_id) for message in messages], messages_total=total, messages_limit=message_limit, messages_offset=message_offset, runs=[RunHistoryResponse(run_id=run.id, status=run.status, created_at=run.created_at, started_at=run.started_at, completed_at=run.completed_at, error=run.error, metrics=RunMetricsResponse.model_validate(run.metrics) if run.metrics else None, charts=[ChartSpec.model_validate(chart) for chart in (getattr(run, "chart_specs", None) or [])], sources=[AnswerSource.model_validate(source) for source in (getattr(run, "answer_sources", None) or [])], caveats=list(getattr(run, "answer_caveats", None) or [])) for run in runs])


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(conversation_id: UUID, request: ConversationTitleRequest, store: ConversationStore = Depends(get_conversation_store)) -> ConversationResponse:
    conversation = await store.update_title(conversation_id, request.title)
    if conversation is None: raise HTTPException(status_code=404, detail={"code": "unknown_conversation", "message": "Conversation not found."})
    return _conversation(conversation)


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: UUID, store: ConversationStore = Depends(get_conversation_store)) -> Response:
    if not await store.delete_conversation(conversation_id): raise HTTPException(status_code=404, detail={"code": "unknown_conversation", "message": "Conversation not found."})
    return Response(status_code=204)
