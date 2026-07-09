"""
Conversation slice — request/response schemas.

Field names mirror the ORM model 1:1 by design (Sprint 1 has no
projection/aggregation needs yet); that will diverge naturally once
later sprints add derived fields (e.g. transcript summaries) that
don't belong on the DB row itself.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.conversation.enums import ConversationSource, ConversationStatus


class ConversationCreateData(BaseModel):
    """Returned by POST /conversations — intentionally minimal per spec."""

    id: uuid.UUID
    status: ConversationStatus


class ConversationListItem(BaseModel):
    """One row in GET /conversations."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    status: ConversationStatus
    file_size: int
    created_at: datetime


class ConversationDetail(BaseModel):
    """Full detail for GET /conversations/{id}."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    filename: str
    mime_type: str
    file_size: int
    duration_seconds: int | None
    status: ConversationStatus
    source: ConversationSource
    created_at: datetime
    updated_at: datetime
