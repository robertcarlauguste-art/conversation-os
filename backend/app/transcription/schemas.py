import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.transcription.enums import TranscriptionStatus


class TranscriptDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    text: str | None
    language: str | None
    status: TranscriptionStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime
