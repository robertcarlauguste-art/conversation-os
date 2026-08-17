"""
Memory ORM models.

Memory is the durable representation of a processed conversation.

Child entities:
- Decision: commitments or choices made
- ActionItem: tasks extracted from conversations
- Person: participants/entities discovered during conversations

These are separate tables intentionally so future features can:
- search independently
- deduplicate entities
- assign ownership
- connect people to clients
- track workflow state
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    ARRAY,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.memory.enums import MemoryType
from app.models.base import Base


class PersonType(str, PyEnum):
    """
    Classification of extracted people/entities.
    """

    CLIENT = "CLIENT"
    CONTACT = "CONTACT"
    AGENT = "AGENT"
    VENDOR = "VENDOR"
    EMPLOYEE = "EMPLOYEE"
    UNKNOWN = "UNKNOWN"


class ActionStatus(str, PyEnum):
    """
    Lifecycle state for extracted tasks.
    """

    OPEN = "OPEN"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Memory(Base):
    __tablename__ = "memories"

    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            name="uq_memories_conversation_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    memory_type: Mapped[MemoryType] = mapped_column(
        Enum(
            MemoryType,
            name="memory_type",
        ),
        nullable=False,
        default=MemoryType.CONVERSATION_SUMMARY,
    )

    topics: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    decisions: Mapped[list["Decision"]] = relationship(
        back_populates="memory",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    action_items: Mapped[list["ActionItem"]] = relationship(
        back_populates="memory",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    people: Mapped[list["Person"]] = relationship(
        back_populates="memory",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "memories.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    memory: Mapped["Memory"] = relationship(
        back_populates="decisions",
    )


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "memories.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    task: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    due: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    owner: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[ActionStatus] = mapped_column(
        Enum(
            ActionStatus,
            name="action_status",
        ),
        nullable=False,
        default=ActionStatus.OPEN,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    memory: Mapped["Memory"] = relationship(
        back_populates="action_items",
    )


class Person(Base):
    __tablename__ = "people"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "memories.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    entity_type: Mapped[PersonType] = mapped_column(
        Enum(
            PersonType,
            name="person_type",
        ),
        nullable=False,
        default=PersonType.UNKNOWN,
    )

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "clients.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    memory: Mapped["Memory"] = relationship(
        back_populates="people",
    )

    client: Mapped["Client | None"] = relationship(
        back_populates="people",
        lazy="selectin",
    )


# Imported at the bottom to avoid circular imports.
from app.client.models import Client