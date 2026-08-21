import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.models import Conversation
from app.memory.models import ActionItem, ActionStatus, Memory, Person
from app.repositories.base import BaseRepository


class MemoryRepository(BaseRepository[Memory]):
    def __init__(self, session: AsyncSession, owner_id: str = "dev_user") -> None:
        super().__init__(session, Memory)
        self.owner_id = owner_id

    async def get(self, id_: object) -> Memory | None:
        result = await self.session.execute(
            select(Memory)
            .join(Conversation, Memory.conversation_id == Conversation.id)
            .where(Memory.id == id_, Conversation.owner_id == self.owner_id)
        )
        return result.scalar_one_or_none()

    async def get_by_conversation_id(self, conversation_id: uuid.UUID) -> Memory | None:
        result = await self.session.execute(
            select(Memory)
            .join(Conversation, Memory.conversation_id == Conversation.id)
            .where(
                Memory.conversation_id == conversation_id,
                Conversation.owner_id == self.owner_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Memory]:
        result = await self.session.execute(
            select(Memory)
            .join(Conversation, Memory.conversation_id == Conversation.id)
            .where(Conversation.owner_id == self.owner_id)
            .order_by(Memory.created_at.desc())
        )
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

    async def get_action_item(self, action_item_id: uuid.UUID) -> ActionItem | None:
        result = await self.session.execute(
            select(ActionItem)
            .join(Memory, ActionItem.memory_id == Memory.id)
            .join(Conversation, Memory.conversation_id == Conversation.id)
            .where(
                ActionItem.id == action_item_id,
                Conversation.owner_id == self.owner_id,
            )
        )
        return result.scalar_one_or_none()

    async def set_action_item_status(
        self,
        action_item: ActionItem,
        status: ActionStatus,
        completed_at=None,
    ) -> ActionItem:
        action_item.status = status
        action_item.completed_at = completed_at
        await self.session.commit()
        await self.session.refresh(action_item)
        return action_item
