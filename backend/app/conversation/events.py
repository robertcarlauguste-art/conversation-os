"""
Conversation domain events.

`ConversationUploaded` was the first domain event, with no consumers
at the time. Sprint 2's orchestrator (app/orchestrator/
conversation_processing.py) is its first real consumer, and adds two
more lifecycle events here: `ConversationProcessingStarted` and
`ConversationProcessed`. Still no message broker — emitting means
logging in a structured, greppable way, called directly by the
orchestrator in sequence.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

logger = logging.getLogger("conversation_os.events")


@dataclass(frozen=True)
class ConversationUploaded:
    conversation_id: uuid.UUID
    filename: str
    occurred_at: datetime


@dataclass(frozen=True)
class ConversationProcessingStarted:
    conversation_id: uuid.UUID
    occurred_at: datetime


@dataclass(frozen=True)
class ConversationProcessed:
    conversation_id: uuid.UUID
    occurred_at: datetime


def emit_conversation_uploaded(conversation_id: uuid.UUID, filename: str) -> ConversationUploaded:
    event = ConversationUploaded(
        conversation_id=conversation_id,
        filename=filename,
        occurred_at=datetime.now(UTC),
    )
    logger.info(
        "event=ConversationUploaded conversation_id=%s",
        event.conversation_id,
    )
    return event


def emit_conversation_processing_started(
    conversation_id: uuid.UUID,
) -> ConversationProcessingStarted:
    event = ConversationProcessingStarted(
        conversation_id=conversation_id, occurred_at=datetime.now(UTC)
    )
    logger.info("event=ConversationProcessingStarted conversation_id=%s", event.conversation_id)
    return event


def emit_conversation_processed(conversation_id: uuid.UUID) -> ConversationProcessed:
    event = ConversationProcessed(conversation_id=conversation_id, occurred_at=datetime.now(UTC))
    logger.info("event=ConversationProcessed conversation_id=%s", event.conversation_id)
    return event
