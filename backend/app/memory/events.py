import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

logger = logging.getLogger("conversation_os.events")


@dataclass(frozen=True)
class MemoryCreated:
    conversation_id: uuid.UUID
    memory_id: uuid.UUID
    occurred_at: datetime


@dataclass(frozen=True)
class ActionItemsExtracted:
    conversation_id: uuid.UUID
    memory_id: uuid.UUID
    count: int
    occurred_at: datetime


def emit_memory_created(conversation_id: uuid.UUID, memory_id: uuid.UUID) -> MemoryCreated:
    event = MemoryCreated(
        conversation_id=conversation_id, memory_id=memory_id, occurred_at=datetime.now(UTC)
    )
    logger.info(
        "event=MemoryCreated conversation_id=%s memory_id=%s",
        event.conversation_id,
        event.memory_id,
    )
    return event


def emit_action_items_extracted(
    conversation_id: uuid.UUID, memory_id: uuid.UUID, count: int
) -> ActionItemsExtracted:
    event = ActionItemsExtracted(
        conversation_id=conversation_id,
        memory_id=memory_id,
        count=count,
        occurred_at=datetime.now(UTC),
    )
    logger.info(
        "event=ActionItemsExtracted conversation_id=%s memory_id=%s count=%d",
        event.conversation_id,
        event.memory_id,
        event.count,
    )
    return event
