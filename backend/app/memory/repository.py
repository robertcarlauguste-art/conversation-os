import uuid

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.models import Client
from app.conversation.models import Conversation
from app.memory.models import ActionItem, ActionStatus, Decision, Memory, Person
from app.repositories.base import BaseRepository


class MemoryRepository(BaseRepository[Memory]):
    async def confirm_person(
        self, memory_id: uuid.UUID, person_id: uuid.UUID, client_id: uuid.UUID | None
    ) -> Person | None:
        person = await self.session.scalar(
            select(Person)
            .join(Memory)
            .join(Conversation)
            .where(
                Person.id == person_id,
                Memory.id == memory_id,
                Conversation.owner_id == self.owner_id,
            )
            .with_for_update(of=Person)
        )
        if person is None:
            return None
        if client_id is None:
            person.confirmed_name = None
            person.client_id = None
        else:
            client = await self.session.scalar(
                select(Client).where(Client.id == client_id, Client.owner_id == self.owner_id)
            )
            if client is None:
                return None
            person.client_id = client.id
            person.confirmed_name = client.full_name
        await self.session.commit()
        await self.session.refresh(person)
        return person

    async def edit_item(
        self,
        memory_id: uuid.UUID,
        item_id: uuid.UUID,
        model: type[ActionItem] | type[Decision],
        values: dict,
    ) -> ActionItem | Decision | None:
        item = await self.session.scalar(
            select(model)
            .join(Memory, model.memory_id == Memory.id)
            .join(Conversation, Memory.conversation_id == Conversation.id)
            .where(
                model.id == item_id, Memory.id == memory_id, Conversation.owner_id == self.owner_id
            )
            .with_for_update(of=model)
        )
        if not isinstance(item, (ActionItem, Decision)):
            return None
        if item.original is None:
            item.original = {key: getattr(item, key) for key in values}
        for key, value in values.items():
            setattr(item, key, value or None if key in ("owner", "due") else value)
        # Edited task wording must invalidate previously suggested completions.
        await self.session.execute(
            update(Conversation)
            .where(
                Conversation.id
                == select(Memory.conversation_id).where(Memory.id == memory_id).scalar_subquery(),
                Conversation.owner_id == self.owner_id,
            )
            .values(updated_at=func.now())
        )
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def set_missing_conversation_title(self, conversation_id: uuid.UUID, title: str) -> None:
        await self.session.execute(
            update(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.owner_id == self.owner_id,
                or_(Conversation.title.is_(None), Conversation.title == ""),
            )
            .values(title=title)
        )

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
        result = await self.session.execute(
            select(Person)
            .join(Memory, Person.memory_id == Memory.id)
            .join(Conversation, Memory.conversation_id == Conversation.id)
            .where(Person.id == person_id, Conversation.owner_id == self.owner_id)
        )
        person = result.scalar_one_or_none()
        client = await self.session.scalar(
            select(Client).where(Client.id == client_id, Client.owner_id == self.owner_id)
        )
        if person is None or client is None:
            raise ValueError("Person or client not found.")
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
