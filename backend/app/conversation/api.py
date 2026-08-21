"""
Conversation API routes.

Thin per Rule 1: parse input, call the service, shape the response.
No business logic lives here — validation rules live in
validators.py, persistence in repository.py, decisions in service.py.

Mounted by app/api/router.py (the composition root) under /api/v1 —
this module only defines routes relative to its own prefix.

Sprint 2 note: upload triggers the full processing pipeline
(transcription + memory extraction) synchronously, inside this
request — see TD-003 in Sprint2.md for why that's a deliberate,
tracked tradeoff rather than a background job.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.conversation.enums import ConversationStatus
from app.conversation.repository import ConversationRepository
from app.conversation.schemas import (
    ConversationCreateData,
    ConversationDetail,
    ConversationListItem,
)
from app.conversation.service import ConversationNotFoundError, ConversationService
from app.conversation.storage import StorageBackend
from app.conversation.storage_factory import build_storage_backend
from app.conversation.validators import ValidationError
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.orchestrator.dependencies import build_conversation_processing_orchestrator
from app.processing.queue import enqueue_conversation_processing
from app.schemas.envelope import ApiResponse

logger = logging.getLogger("conversation_os.conversation")

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_storage_backend(settings: Settings = Depends(get_settings)) -> StorageBackend:
    return build_storage_backend(settings)


def get_conversation_service(
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
    storage: StorageBackend = Depends(get_storage_backend),
    settings: Settings = Depends(get_settings),
) -> ConversationService:
    repository = ConversationRepository(session, principal.user_id)
    return ConversationService(
        repository,
        storage,
        allowed_mime_types=settings.allowed_audio_mime_types,
        max_upload_size_bytes=settings.max_upload_size_bytes,
    )


@router.post("", response_model=ApiResponse[ConversationCreateData])
async def upload_conversation(
    file: UploadFile,
    principal: CurrentPrincipal,
    title: str | None = None,
    service: ConversationService = Depends(get_conversation_service),
    session: AsyncSession = Depends(get_db_session),
    storage: StorageBackend = Depends(get_storage_backend),
    settings: Settings = Depends(get_settings),
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

    # Upload has already succeeded at this point (file stored, row
    # persisted) — a processing failure below must not turn into an
    # HTTP error for the upload itself, only into status=FAILED.
    try:
        if settings.processing_mode == "queue":
            await enqueue_conversation_processing(conversation.id, principal.user_id, settings)
            conversation = await service.update_status(conversation.id, ConversationStatus.QUEUED)
        else:
            orchestrator = build_conversation_processing_orchestrator(
                session, storage, settings, principal.user_id
            )
            await orchestrator.run(conversation.id)
    except Exception:
        logger.warning(
            "conversation_processing_failed_during_upload conversation_id=%s",
            conversation.id,
            exc_info=True,
        )
        if conversation.status not in (ConversationStatus.COMPLETED, ConversationStatus.FAILED):
            await service.update_status(conversation.id, ConversationStatus.FAILED)

    return ApiResponse(
        success=True,
        data=ConversationCreateData(id=conversation.id, status=conversation.status),
    )


@router.get("", response_model=ApiResponse[list[ConversationListItem]])
async def list_conversations(
    service: ConversationService = Depends(get_conversation_service),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    status: ConversationStatus | None = Query(default=None),
) -> ApiResponse[list[ConversationListItem]]:
    conversations = await service.list_conversations(
        limit=limit,
        offset=offset,
        search=search,
        status=status.value if status else None,
    )
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
