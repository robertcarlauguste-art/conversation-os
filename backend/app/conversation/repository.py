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
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Conversation)

    async def list_all(self) -> list[Conversation]:
        """Newest first, per GET /conversations spec."""
        result = await self.session.execute(
            select(Conversation).order_by(Conversation.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_by_id(self, conversation_id: uuid.UUID) -> None:
        await self.session.execute(
            sql_delete(Conversation).where(Conversation.id == conversation_id)
        )
        await self.session.commit()
