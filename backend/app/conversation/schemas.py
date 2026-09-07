"""
Conversation slice — request/response schemas.

Field names mirror the ORM model 1:1 by design (Sprint 1 has no
projection/aggregation needs yet); that will diverge naturally once
later sprints add derived fields (e.g. transcript summaries) that
don't belong on the DB row itself.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field, field_validator

from app.conversation.enums import ConversationSource, ConversationStatus
from app.processing.visibility import is_stale, safe_error, stale_threshold_seconds


class ConversationCreateData(BaseModel):
    """Returned by POST /conversations — intentionally minimal per spec."""

    id: uuid.UUID
    status: ConversationStatus


class ProcessingVisibility(BaseModel):
    status: ConversationStatus
    created_at: datetime
    processing_started_at: datetime | None = None
    processing_error: str | None = None

    @field_validator("processing_error")
    @classmethod
    def sanitize_error(cls, value: str | None) -> str | None:
        return safe_error(value)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_stale(self) -> bool:
        return is_stale(self.status, self.created_at, self.processing_started_at)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def stale_threshold_seconds(self) -> int:
        return stale_threshold_seconds()


class ConversationListItem(ProcessingVisibility):
    """One row in GET /conversations."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    status: ConversationStatus
    file_size: int
    created_at: datetime
    processing_attempts: int = 0
    processing_error: str | None = None


class ConversationDetail(ProcessingVisibility):
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
    client_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    processing_attempts: int = 0
    processing_error: str | None = None
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
