"""
Transcription domain events. Same pattern as conversation/events.py:
emitting means logging in a structured, greppable way. No message
broker — the orchestrator calls these directly and synchronously.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from app.processing.visibility import safe_error

logger = logging.getLogger("conversation_os.events")


@dataclass(frozen=True)
class TranscriptionCompleted:
    conversation_id: uuid.UUID
    transcript_id: uuid.UUID
    occurred_at: datetime


@dataclass(frozen=True)
class TranscriptionFailed:
    conversation_id: uuid.UUID
    error: str
    occurred_at: datetime


def emit_transcription_completed(
    conversation_id: uuid.UUID, transcript_id: uuid.UUID
) -> TranscriptionCompleted:
    event = TranscriptionCompleted(
        conversation_id=conversation_id,
        transcript_id=transcript_id,
        occurred_at=datetime.now(UTC),
    )
    logger.info(
        "event=TranscriptionCompleted conversation_id=%s transcript_id=%s",
        event.conversation_id,
        event.transcript_id,
    )
    return event


def emit_transcription_failed(conversation_id: uuid.UUID, error: str) -> TranscriptionFailed:
    error = safe_error(error) or "Processing failed."
    event = TranscriptionFailed(
        conversation_id=conversation_id, error=error, occurred_at=datetime.now(UTC)
    )
    logger.warning(
        "event=TranscriptionFailed conversation_id=%s error=%s", event.conversation_id, error
    )
    return event
