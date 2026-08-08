"""
Transcript ORM model.

One transcript per conversation (enforced with a unique constraint on
`conversation_id`, not a foreign-key relationship object — the
transcription slice knows a conversation_id exists, not the
Conversation model itself, keeping slices from importing each other's
models per ADR-004).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.transcription.enums import TranscriptionStatus


class Transcript(Base):
    __tablename__ = "transcripts"
    __table_args__ = (UniqueConstraint("conversation_id", name="uq_transcripts_conversation_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[TranscriptionStatus] = mapped_column(
        Enum(TranscriptionStatus, name="transcription_status"),
        nullable=False,
        default=TranscriptionStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
