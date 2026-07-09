"""
Conversation API routes.

Thin per Rule 1: parse input, call the service, shape the response.
No business logic lives here — validation rules live in
validators.py, persistence in repository.py, decisions in service.py.

Mounted by app/api/router.py (the composition root) under /api/v1 —
this module only defines routes relative to its own prefix.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.repository import ConversationRepository
from app.conversation.schemas import (
    ConversationCreateData,
    ConversationDetail,
    ConversationListItem,
)
from app.conversation.service import ConversationNotFoundError, ConversationService
from app.conversation.storage import LocalStorageBackend, StorageBackend
from app.conversation.validators import ValidationError
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.schemas.envelope import ApiResponse

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_storage_backend(settings: Settings = Depends(get_settings)) -> StorageBackend:
    return LocalStorageBackend(root=settings.storage_root)


def get_conversation_service(
    session: AsyncSession = Depends(get_db_session),
    storage: StorageBackend = Depends(get_storage_backend),
    settings: Settings = Depends(get_settings),
) -> ConversationService:
    repository = ConversationRepository(session)
    return ConversationService(
        repository,
        storage,
        allowed_mime_types=settings.allowed_audio_mime_types,
        max_upload_size_bytes=settings.max_upload_size_bytes,
    )


@router.post("", response_model=ApiResponse[ConversationCreateData])
async def upload_conversation(
    file: UploadFile,
    title: str | None = None,
    service: ConversationService = Depends(get_conversation_service),
) -> ApiResponse[ConversationCreateData]:
    content = await file.read()
    try:
        conversation = await service.upload(
            filename=file.filename or "unknown",
            content_type=file.content_type,
            content=content,
            title=title,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ApiResponse(
        success=True,
        data=ConversationCreateData(id=conversation.id, status=conversation.status),
    )


@router.get("", response_model=ApiResponse[list[ConversationListItem]])
async def list_conversations(
    service: ConversationService = Depends(get_conversation_service),
) -> ApiResponse[list[ConversationListItem]]:
    conversations = await service.list_conversations()
    return ApiResponse(
        success=True,
        data=[ConversationListItem.model_validate(c) for c in conversations],
    )


@router.get("/{conversation_id}", response_model=ApiResponse[ConversationDetail])
async def get_conversation(
    conversation_id: uuid.UUID,
    service: ConversationService = Depends(get_conversation_service),
) -> ApiResponse[ConversationDetail]:
    try:
        conversation = await service.get_conversation(conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ApiResponse(success=True, data=ConversationDetail.model_validate(conversation))


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    service: ConversationService = Depends(get_conversation_service),
) -> None:
    try:
        await service.delete_conversation(conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
