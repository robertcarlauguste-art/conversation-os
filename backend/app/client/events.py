import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

logger = logging.getLogger("conversation_os.events")


@dataclass(frozen=True)
class ClientCreated:
    client_id: uuid.UUID
    conversation_id: uuid.UUID
    occurred_at: datetime


@dataclass(frozen=True)
class ClientMatched:
    client_id: uuid.UUID
    conversation_id: uuid.UUID
    occurred_at: datetime


@dataclass(frozen=True)
class ClientProfileUpdated:
    client_id: uuid.UUID
    conversation_id: uuid.UUID
    fact_count: int
    occurred_at: datetime


def emit_client_created(client_id: uuid.UUID, conversation_id: uuid.UUID) -> ClientCreated:
    event = ClientCreated(
        client_id=client_id, conversation_id=conversation_id, occurred_at=datetime.now(UTC)
    )
    logger.info(
        "event=ClientCreated client_id=%s conversation_id=%s", event.client_id, conversation_id
    )
    return event


def emit_client_matched(client_id: uuid.UUID, conversation_id: uuid.UUID) -> ClientMatched:
    event = ClientMatched(
        client_id=client_id, conversation_id=conversation_id, occurred_at=datetime.now(UTC)
    )
    logger.info(
        "event=ClientMatched client_id=%s conversation_id=%s", event.client_id, conversation_id
    )
    return event


def emit_client_profile_updated(
    client_id: uuid.UUID, conversation_id: uuid.UUID, fact_count: int
) -> ClientProfileUpdated:
    event = ClientProfileUpdated(
        client_id=client_id,
        conversation_id=conversation_id,
        fact_count=fact_count,
        occurred_at=datetime.now(UTC),
    )
    logger.info(
        "event=ClientProfileUpdated client_id=%s conversation_id=%s fact_count=%d",
        event.client_id,
        conversation_id,
        fact_count,
    )
    return event
