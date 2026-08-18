import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ClientFollowupAction


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
