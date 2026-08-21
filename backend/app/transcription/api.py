"""
Transcription API routes. Read-only this sprint — transcripts are
created by the orchestrator, not via a direct API call.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.core.database import get_db_session
from app.schemas.envelope import ApiResponse
from app.transcription.repository import TranscriptRepository
from app.transcription.schemas import TranscriptDetail

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
