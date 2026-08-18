import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ClientFollowupAction
from app.client.models import Client
from app.conversation.models import Conversation
from app.memory.models import ActionItem, ActionStatus, Memory


@dataclass(frozen=True)
class OpenActionRecord:
    action_item: ActionItem
    conversation_id: uuid.UUID
    conversation_title: str | None
    client_id: uuid.UUID | None
    client_name: str | None


@dataclass(frozen=True)
class FollowupActivityRecord:
    action: ClientFollowupAction
    client_name: str


class DashboardRepository:
    """
    Dashboard-specific data access.

    The dashboard currently aggregates data owned by other domain
    slices, so this repository stays intentionally thin until we
    introduce dashboard-specific queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_latest_followup_actions(
        self,
    ) -> dict[uuid.UUID, ClientFollowupAction]:
        result = await self.session.execute(
            select(ClientFollowupAction).order_by(
                ClientFollowupAction.client_id,
                ClientFollowupAction.created_at.desc(),
                ClientFollowupAction.id.desc(),
            )
        )
        latest: dict[uuid.UUID, ClientFollowupAction] = {}
        for action in result.scalars():
            latest.setdefault(action.client_id, action)
        return latest

    async def add_followup_action(
        self,
        action: ClientFollowupAction,
    ) -> ClientFollowupAction:
        self.session.add(action)
        await self.session.commit()
        await self.session.refresh(action)
        return action

    async def list_open_action_items(self, limit: int = 100) -> list[OpenActionRecord]:
        result = await self.session.execute(
            select(ActionItem, Memory, Conversation, Client)
            .join(Memory, ActionItem.memory_id == Memory.id)
            .join(Conversation, Memory.conversation_id == Conversation.id)
            .outerjoin(Client, Conversation.client_id == Client.id)
            .where(ActionItem.status == ActionStatus.OPEN)
            .order_by(ActionItem.created_at.desc(), ActionItem.id.desc())
            .limit(limit)
        )
        return [
            OpenActionRecord(
                action_item=action_item,
                conversation_id=conversation.id,
                conversation_title=conversation.title,
                client_id=client.id if client is not None else None,
                client_name=client.full_name if client is not None else None,
            )
            for action_item, _memory, conversation, client in result.all()
        ]

    async def list_recent_followup_activity(
        self,
        limit: int = 10,
    ) -> list[FollowupActivityRecord]:
        result = await self.session.execute(
            select(ClientFollowupAction, Client)
            .join(Client, ClientFollowupAction.client_id == Client.id)
            .order_by(
                ClientFollowupAction.created_at.desc(),
                ClientFollowupAction.id.desc(),
            )
            .limit(limit)
        )
        return [
            FollowupActivityRecord(
                action=action,
                client_name=client.full_name,
            )
            for action, client in result.all()
        ]
