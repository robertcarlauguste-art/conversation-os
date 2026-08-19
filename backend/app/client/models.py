"""
Client and ClientFact ORM models.

`Client` is a durable identity independent of any single conversation
(unlike Sprint 2's `Memory`, which is one-per-conversation). `people`
and `conversations` gain a nullable `client_id` FK once a person or
conversation has been reconciled to a client.

`ClientFact` retains provenance on every row (FD-005): which
conversation and which memory extraction produced it. Facts are
immutable and append-only.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.models.base import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    role: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
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

    facts: Mapped[list["ClientFact"]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    people: Mapped[list["Person"]] = relationship(
        back_populates="client",
        lazy="selectin",
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="client",
        lazy="selectin",
    )


class ClientFact(Base):
    __tablename__ = "client_facts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "clients.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    fact_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source_conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    source_memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "memories.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    client: Mapped["Client"] = relationship(
        back_populates="facts",
    )


# Imported at the bottom to avoid circular imports.
from app.conversation.models import Conversation  # noqa: E402
from app.memory.models import Person  # noqa: E402
