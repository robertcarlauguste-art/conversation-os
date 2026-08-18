"""
Memory slice schemas.

`ExtractionResult` is the schema-validation step in the pipeline:

Conversation
    →
LLM
    →
Structured JSON
    →
Pydantic Validation
    →
Persistence

The LLM returns structured memory data.
This module validates that structure before anything reaches
the database.
"""


import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.memory.models import PersonType



# ============================================================
# LLM EXTRACTION SCHEMAS
# ============================================================


class ExtractedActionItem(BaseModel):
    """
    Rich action item extracted from conversation.

    Example:

    {
        "task": "Schedule a home showing",
        "due": "Next Tuesday",
        "assignee": "Sarah"
    }
    """

    task: str

    due: str | None = None

    assignee: str | None = None



class ExtractedPerson(BaseModel):
    """
    Person/entity extracted from conversation.

    Example:

    {
        "name": "Sarah",
        "role": "Realtor, ABC Realty",
        "entity_type": "AGENT"
    }


    Supported entity types:

    CLIENT
    CONTACT
    AGENT
    VENDOR
    EMPLOYEE
    UNKNOWN
    """

    name: str

    role: str | None = None

    entity_type: PersonType = PersonType.UNKNOWN



class ExtractionResult(BaseModel):
    """
    Final validated structure returned from LLM extraction.
    """


    summary: str


    decisions: list[str] = Field(
        default_factory=list
    )


    action_items: list[ExtractedActionItem] = Field(
        default_factory=list
    )


    people: list[ExtractedPerson] = Field(
        default_factory=list
    )


    topics: list[str] = Field(
        default_factory=list
    )


    confidence: float = Field(
        ge=0,
        le=1,
    )




# ============================================================
# API RESPONSE SCHEMAS
# ============================================================


class DecisionOut(BaseModel):

    model_config = ConfigDict(
        from_attributes=True
    )


    id: uuid.UUID

    description: str




class ActionItemOut(BaseModel):

    model_config = ConfigDict(
        from_attributes=True
    )


    id: uuid.UUID

    task: str

    due: str | None

    owner: str | None

    status: str




class PersonOut(BaseModel):

    model_config = ConfigDict(
        from_attributes=True
    )


    id: uuid.UUID

    name: str

    role: str | None

    entity_type: PersonType

    client_id: uuid.UUID | None




class MemoryDetail(BaseModel):

    model_config = ConfigDict(
        from_attributes=True
    )


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

    model_config = ConfigDict(
        from_attributes=True
    )


    id: uuid.UUID


    conversation_id: uuid.UUID


    title: str | None


    summary: str


    confidence: float


    created_at: datetime
