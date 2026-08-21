"""
Conversation repository.

Subclasses `app/repositories/base.py`'s `BaseRepository`, exactly as
planned in ADR-002 — this is the first concrete repository in the
codebase. Adds the query methods `BaseRepository` doesn't have
(list-all, sorted; delete) since those are specific to how
Conversation is queried, not generic to every entity.
"""

import uuid

from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.models import Conversation
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, session: AsyncSession, owner_id: str = "dev_user") -> None:
        super().__init__(session, Conversation)
        self.owner_id = owner_id

    async def get(self, id_: object) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == id_, Conversation.owner_id == self.owner_id
            )
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        search: str | None = None,
        status: str | None = None,
    ) -> list[Conversation]:
        """Newest first, per GET /conversations spec."""
        query = select(Conversation).where(Conversation.owner_id == self.owner_id)
        if search:
            term = f"%{search.strip()}%"
            query = query.where(Conversation.title.ilike(term) | Conversation.filename.ilike(term))
        if status:
            query = query.where(Conversation.status == status)
        query = query.order_by(Conversation.created_at.desc()).offset(offset)
        if limit is not None:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_by_id(self, conversation_id: uuid.UUID) -> None:
        await self.session.execute(
            sql_delete(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.owner_id == self.owner_id,
            )
        )
        await self.session.commit()

    async def list_by_client_id(self, client_id: uuid.UUID) -> list[Conversation]:
        """Sprint 3 — supports GET /clients/{id}/conversations (US-104)."""
        result = await self.session.execute(
            select(Conversation)
            .where(
                Conversation.client_id == client_id,
                Conversation.owner_id == self.owner_id,
            )
            .order_by(Conversation.created_at.desc())
        )
        return list(result.scalars().all())
