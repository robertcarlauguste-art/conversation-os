import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.models import Memory, Person
from app.repositories.base import BaseRepository


class MemoryRepository(BaseRepository[Memory]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Memory)

    async def get_by_conversation_id(self, conversation_id: uuid.UUID) -> Memory | None:
        result = await self.session.execute(
            select(Memory).where(Memory.conversation_id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Memory]:
        result = await self.session.execute(select(Memory).order_by(Memory.created_at.desc()))
        return list(result.scalars().all())

    async def set_person_client(self, person_id: uuid.UUID, client_id: uuid.UUID) -> None:
        """
        Sprint 3: links an already-persisted Person row to the Client
        the orchestrator's reconciliation stage matched or created for
        them. `Person` rows are created inside `extract_and_persist`'s
        transaction (Sprint 2); reconciliation happens in a later
        orchestrator stage, so this is a separate, small update rather
        than something `extract_and_persist` could have done itself —
        it doesn't know about clients, by design (Rule 5).
        """
        person = await self.session.get(Person, person_id)
        if person is not None:
            person.client_id = client_id
            await self.session.commit()
