"""
Conversation domain events.

`ConversationUploaded` is the first domain event in the system. It
has no consumers yet — future sprints (transcription, in particular)
will subscribe to it. For now, emitting it means logging it in a
structured, greppable way, so the event's existence is visible in
logs even before anything listens for it.

If a second slice needs to publish/subscribe to events, promote the
publish mechanism to a shared `app/orchestrator` or event-bus module
rather than duplicating this pattern per slice — noted in ADR-004.
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


def emit_conversation_uploaded(conversation_id: uuid.UUID, filename: str) -> ConversationUploaded:
    event = ConversationUploaded(
        conversation_id=conversation_id,
        filename=filename,
        occurred_at=datetime.now(UTC),
    )
    logger.info(
        "event=ConversationUploaded conversation_id=%s filename=%s",
        event.conversation_id,
        event.filename,
    )
    return event
