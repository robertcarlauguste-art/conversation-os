"""
Client and ClientFact ORM models.

`Client` is a durable identity independent of any single conversation
(unlike Sprint 2's `Memory`, which is one-per-conversation). `people`
and `conversations` (Sprint 1/2 tables) gain a nullable `client_id`
FK once a person/conversation is reconciled to a client — see the
migration for both sides of that change.

`ClientFact` retains provenance on every row (FD-005): which
conversation and which memory-extraction produced it, plus the
timestamp the row was created (its extraction time). Facts are never
edited after creation — each mention/extraction event that produces
a fact for an already-known client adds a new row rather than
updating an existing one, so provenance is never lost to an update.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Last-reconciled role (e.g. "buyer", "seller") — the corroborating
    # attribute FD-003 requires alongside name. Deliberately NOT a
    # cross-slice query against memory/people at match time (that would
    # couple this repository to another slice's table); instead the
    # signal is captured here when a match/create happens. A person
    # whose role differs from what's on file won't auto-match against
    # this client (falls back to manual review, US-105) — conservative
    # by design, matching FD-003's "never merge on name alone" intent.
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    facts: Mapped[list["ClientFact"]] = relationship(
        back_populates="client", cascade="all, delete-orphan", lazy="selectin"
    )


class ClientFact(Base):
    __tablename__ = "client_facts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    fact_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Provenance (FD-005) — required on every row, not optional.
    source_conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    source_memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memories.id", ondelete="CASCADE"), nullable=False
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # This timestamp IS the "extraction timestamp" FD-005 requires —
    # facts are immutable once created, so created_at never drifts
    # from the moment the fact was actually extracted.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    client: Mapped["Client"] = relationship(back_populates="facts")
