"""
Conversation ORM model — the first real business entity.

Subclasses the shared `Base` from app/models/base.py so Alembic
autogenerate can see it, per the plan laid out in ADR-002/ADR-004:
domain packages own their concrete models; only the declarative base
itself is shared infrastructure.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.conversation.enums import ConversationSource, ConversationStatus
from app.models.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus, name="conversation_status"),
        nullable=False,
        default=ConversationStatus.UPLOADED,
    )
    source: Mapped[ConversationSource] = mapped_column(
        Enum(ConversationSource, name="conversation_source"),
        nullable=False,
        default=ConversationSource.UPLOAD,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
