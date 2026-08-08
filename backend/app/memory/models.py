"""
Memory ORM models.

`Memory` is the parent row (one per conversation, this sprint).
`Decision`, `ActionItem`, and `Person` are child rows — modeled as
their own tables (not JSON blobs) specifically so future sprints can
query, dedupe, or link them independently, per the spec's "model so
future features can build on them." Topics are simple enough (a flat
list of strings, no independent lifecycle yet) to store as an array
column on Memory rather than a fifth table — revisit if a future
sprint needs to query or dedupe topics across conversations.
"""

import uuid
from datetime import datetime

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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.memory.enums import MemoryType
from app.models.base import Base


class Memory(Base):
    __tablename__ = "memories"
    __table_args__ = (UniqueConstraint("conversation_id", name="uq_memories_conversation_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    memory_type: Mapped[MemoryType] = mapped_column(
        Enum(MemoryType, name="memory_type"),
        nullable=False,
        default=MemoryType.CONVERSATION_SUMMARY,
    )
    topics: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    decisions: Mapped[list["Decision"]] = relationship(
        back_populates="memory", cascade="all, delete-orphan", lazy="selectin"
    )
    action_items: Mapped[list["ActionItem"]] = relationship(
        back_populates="memory", cascade="all, delete-orphan", lazy="selectin"
    )
    people: Mapped[list["Person"]] = relationship(
        back_populates="memory", cascade="all, delete-orphan", lazy="selectin"
    )


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memories.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    memory: Mapped["Memory"] = relationship(back_populates="decisions")


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memories.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    memory: Mapped["Memory"] = relationship(back_populates="action_items")


class Person(Base):
    __tablename__ = "people"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memories.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Sprint 3: set by the orchestrator's reconciliation stage once
    # this person is matched to (or creates) a durable Client. Null
    # until reconciliation runs, and stays null if FD-003's matching
    # requirements aren't met (no role present, most commonly).
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    memory: Mapped["Memory"] = relationship(back_populates="people")
