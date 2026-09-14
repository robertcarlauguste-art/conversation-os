import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.client.models import Client, ClientFact
from app.conversation.models import Conversation
from app.memory.models import Memory, Person
from app.repositories.base import BaseRepository


class ClientRepository(BaseRepository[Client]):
    def __init__(self, session: AsyncSession, owner_id: str = "dev_user") -> None:
        super().__init__(session, Client)
        self.owner_id = owner_id

    def _owned_relations(self):
        owned_conversations = select(Conversation.id).where(Conversation.owner_id == self.owner_id)
        owned_memories = select(Memory.id).where(Memory.conversation_id.in_(owned_conversations))
        return (
            selectinload(Client.conversations.and_(Conversation.owner_id == self.owner_id)),
            selectinload(Client.people.and_(Person.memory_id.in_(owned_memories))),
            selectinload(
                Client.facts.and_(
                    ClientFact.source_conversation_id.in_(owned_conversations),
                    ClientFact.source_memory_id.in_(owned_memories),
                )
            ),
        )

    async def owns_fact_provenance(
        self, client_id: uuid.UUID, conversation_id: uuid.UUID, memory_id: uuid.UUID
    ) -> bool:
        client = await self.get(client_id)
        memory = await self.session.scalar(
            select(Memory.id)
            .join(Conversation, Memory.conversation_id == Conversation.id)
            .where(
                Memory.id == memory_id,
                Conversation.id == conversation_id,
                Conversation.owner_id == self.owner_id,
            )
        )
        return client is not None and memory is not None

    async def get(self, id_: object) -> Client | None:
        result = await self.session.execute(
            select(Client).where(Client.id == id_, Client.owner_id == self.owner_id)
        )
        return result.scalar_one_or_none()

    async def find_corroborated_match(
        self,
        normalized_name: str,
        normalized_role: str,
    ) -> Client | None:
        result = await self.session.execute(
            select(Client).where(
                func.lower(Client.full_name) == normalized_name,
                func.lower(Client.role) == normalized_role,
                Client.owner_id == self.owner_id,
            )
        )

        return result.scalars().first()

    async def get_with_facts(
        self,
        client_id: uuid.UUID,
    ) -> Client | None:
        result = await self.session.execute(
            select(Client)
            .options(*self._owned_relations())
            .where(Client.id == client_id, Client.owner_id == self.owner_id)
            .execution_options(populate_existing=True)
        )

        return result.scalar_one_or_none()

    async def list_all(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        search: str | None = None,
        role: str | None = None,
    ) -> list[Client]:
        query = (
            select(Client)
            .options(*self._owned_relations())
            .where(Client.owner_id == self.owner_id)
            .order_by(Client.updated_at.desc())
            .execution_options(populate_existing=True)
        )
        if search:
            term = f"%{search.strip()}%"
            query = query.where(
                Client.full_name.ilike(term) | Client.email.ilike(term) | Client.phone.ilike(term)
            )
        if role:
            query = query.where(Client.role == role.strip().lower())
        query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        result = await self.session.execute(query)

        return list(result.scalars().all())
