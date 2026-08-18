from datetime import datetime, timezone
from typing import Callable

from app.client.models import Client
from app.client.schemas import ClientListItem
from app.client.service import ClientService
from app.conversation.enums import ConversationStatus
from app.conversation.schemas import ConversationListItem
from app.conversation.service import ConversationService

from .schemas import DashboardOverview, DashboardResponse


class DashboardService:
    FOLLOWUP_AFTER_DAYS = 7

    """
    Aggregates existing business capabilities into the data required
    by the Executive Command Center.

    The dashboard does not own conversation or client persistence.
    It consumes those domain services and shapes their results into
    a dashboard-specific response.
    """

    def __init__(
        self,
        conversation_service: ConversationService,
        client_service: ClientService,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._conversations = conversation_service
        self._clients = client_service
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def _build_alerts(failed: int) -> list[str]:
        if failed == 0:
            return []

        if failed == 1:
            return ["1 conversation failed processing and needs review."]

        return [f"{failed} conversations failed processing and need review."]

    def _build_followups(self, clients: list[Client]) -> list[str]:
        now = self._clock()
        followups: list[str] = []

        for client in clients:
            if not client.conversations:
                followups.append(
                    f"Schedule a first conversation with {client.full_name}."
                )
                continue

            latest = max(
                conversation.created_at
                for conversation in client.conversations
            )
            days_since_contact = (now - latest).days

            if days_since_contact >= self.FOLLOWUP_AFTER_DAYS:
                followups.append(
                    f"Follow up with {client.full_name}; last conversation was "
                    f"{days_since_contact} days ago."
                )

        return followups[:5]

    async def get_dashboard(self) -> DashboardResponse:
        conversations = await self._conversations.list_conversations()
        clients = await self._clients.list_client_profiles()

        overview = DashboardOverview(
            clients=len(clients),
            conversations=len(conversations),
            completed=sum(
                1
                for conversation in conversations
                if conversation.status == ConversationStatus.COMPLETED
            ),
            processing=sum(
                1
                for conversation in conversations
                if conversation.status == ConversationStatus.PROCESSING
            ),
            failed=sum(
                1
                for conversation in conversations
                if conversation.status == ConversationStatus.FAILED
            ),
        )

        alerts = self._build_alerts(overview.failed)
        followups = self._build_followups(clients)

        return DashboardResponse(
            overview=overview,
            recent_clients=[
                ClientListItem.model_validate(client)
                for client in clients[:5]
            ],
            recent_conversations=[
                ConversationListItem.model_validate(conversation)
                for conversation in conversations[:5]
            ],
            alerts=alerts,
            followups=followups,
        )
