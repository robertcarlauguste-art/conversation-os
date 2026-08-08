import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClientFactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fact_text: str
    source_conversation_id: uuid.UUID
    source_memory_id: uuid.UUID
    confidence: float | None
    created_at: datetime


class ClientListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str | None
    phone: str | None
    created_at: datetime


class ClientDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str | None
    phone: str | None
    facts: list[ClientFactOut]
    created_at: datetime
    updated_at: datetime


class ClientConversationItem(BaseModel):
    """One row in GET /clients/{id}/conversations — deliberately minimal."""

    id: uuid.UUID
    title: str | None
    filename: str
    status: str
    created_at: datetime
