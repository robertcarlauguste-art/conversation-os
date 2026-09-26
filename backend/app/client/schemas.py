import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ClientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    full_name: str = Field(min_length=1, max_length=255)


class ClientFactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fact_text: str
    source_conversation_id: uuid.UUID
    source_memory_id: uuid.UUID
    confidence: float | None
    created_at: datetime


class ClientConversationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    filename: str
    summary_preview: str | None = None
    status: str
    created_at: datetime


class ClientPersonItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    role: str | None
    entity_type: str
    created_at: datetime


class ClientListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    role: str | None
    email: str | None
    phone: str | None
    created_at: datetime


class ClientDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    role: str | None
    email: str | None
    phone: str | None

    facts: list[ClientFactOut]
    conversations: list[ClientConversationItem]
    people: list[ClientPersonItem]

    created_at: datetime
    updated_at: datetime
