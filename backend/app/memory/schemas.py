"""
Memory slice schemas.

`ExtractionResult` is the schema-validation step in the pipeline
(Conversation → LLM → Structured JSON → **Validation** → Persistence):
the raw string the LLM returns is parsed and validated against this
before anything touches the database. If the LLM returns malformed
JSON or a field outside the expected shape, this raises here rather
than persisting garbage.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExtractionResult(BaseModel):
    """The shape we require the LLM's JSON output to match."""

    summary: str = Field(min_length=1)
    decisions: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    people: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    description: str


class ActionItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    description: str
    owner: str | None


class PersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    role: str | None
    client_id: uuid.UUID | None


class MemoryDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    title: str | None
    summary: str
    memory_type: str
    topics: list[str]
    confidence: float
    source: str
    decisions: list[DecisionOut]
    action_items: list[ActionItemOut]
    people: list[PersonOut]
    created_at: datetime
    updated_at: datetime


class MemoryListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    title: str | None
    summary: str
    confidence: float
    created_at: datetime
