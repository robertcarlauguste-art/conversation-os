import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.processing.visibility import safe_error
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

    @field_validator("error_message")
    @classmethod
    def sanitize_error(cls, value: str | None) -> str | None:
        return safe_error(value)
