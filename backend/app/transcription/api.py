"""
Transcription reads and owner-scoped corrections. Original transcripts are
created by the orchestrator, not via a direct API call.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal

# Corrections never replace the original transcript or existing memory entities.
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.providers.dependencies import get_ai_provider
from app.schemas.envelope import ApiResponse
from app.transcription.corrections import (
    CorrectionInput,
    CorrectionOut,
    CorrectionRepository,
    PreviewInput,
    generate_preview,
)
from app.transcription.repository import TranscriptRepository
from app.transcription.schemas import TranscriptDetail
from app.usage.service import UsageService

router = APIRouter(prefix="/transcriptions", tags=["transcriptions"])


@router.get("/by-conversation/{conversation_id}", response_model=ApiResponse[TranscriptDetail])
async def get_transcript_by_conversation(
    conversation_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[TranscriptDetail]:
    repository = TranscriptRepository(session, principal.user_id)
    transcript = await repository.get_by_conversation_id(conversation_id)
    if transcript is None:
        raise HTTPException(
            status_code=404, detail=f"No transcript found for conversation {conversation_id}."
        )
    return ApiResponse(success=True, data=TranscriptDetail.model_validate(transcript))


@router.get(
    "/by-conversation/{conversation_id}/correction",
    response_model=ApiResponse[CorrectionOut | None],
)
async def get_correction(
    conversation_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
):
    return ApiResponse(
        success=True,
        data=await CorrectionRepository(session, principal.user_id).get(conversation_id),
    )


@router.put(
    "/by-conversation/{conversation_id}/correction", response_model=ApiResponse[CorrectionOut]
)
async def save_correction(
    conversation_id: uuid.UUID,
    body: CorrectionInput,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
):
    return ApiResponse(
        success=True,
        data=await CorrectionRepository(session, principal.user_id).save(conversation_id, body),
    )


@router.post(
    "/by-conversation/{conversation_id}/correction/preview",
    response_model=ApiResponse[CorrectionOut],
)
async def preview_correction(
    conversation_id: uuid.UUID,
    body: PreviewInput,
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    repo = CorrectionRepository(session, principal.user_id)
    current = await repo.get(conversation_id)
    if current is None or current.version != body.expected_version:
        raise HTTPException(409, "Save your correction before generating updated notes.")
    source, version = current.text, current.version
    if not settings.anthropic_api_key:
        raise HTTPException(503, "Updated notes are temporarily unavailable.")
    await session.commit()
    if settings.pilot_limits_enabled:
        await UsageService(session, principal.user_id).consume_ai()
    preview = await generate_preview(get_ai_provider(settings), source)
    return ApiResponse(
        success=True, data=await repo.store_preview(conversation_id, version, preview)
    )
