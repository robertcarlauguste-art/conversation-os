from datetime import datetime, timezone
from typing import Callable

from app.client.models import Client
from app.client.schemas import ClientListItem
from app.client.service import ClientService
from app.conversation.enums import ConversationStatus
from app.conversation.schemas import ConversationListItem
from app.conversation.service import ConversationService

from .schemas import DashboardOverview, DashboardPriority, DashboardResponse


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

    def _build_priorities(
        self,
        failed: int,
        clients: list[Client],
    ) -> list[DashboardPriority]:
        priorities: list[tuple[int, DashboardPriority]] = []

        if failed:
            noun = "conversation" if failed == 1 else "conversations"
            priorities.append(
                (
                    10_000,
                    DashboardPriority(
                        rank=1,
                        severity="critical",
                        category="processing",
                        title=f"Review {failed} failed {noun}",
                        description=(
                            "Resolve processing failures before they hide "
                            "client information or next actions."
                        ),
                        href="/conversations",
                    ),
                )
            )

        now = self._clock()
        for client in clients:
            if not client.conversations:
                priorities.append(
                    (
                        0,
                        DashboardPriority(
                            rank=1,
                            severity="medium",
                            category="followup",
                            title=f"Start a conversation with {client.full_name}",
                            description="No conversations are linked to this client yet.",
                            href=f"/clients/{client.id}",
                        ),
                    )
                )
                continue

            latest = max(
                conversation.created_at
                for conversation in client.conversations
            )
            days_since_contact = (now - latest).days
            if days_since_contact >= self.FOLLOWUP_AFTER_DAYS:
                priorities.append(
                    (
                        days_since_contact,
                        DashboardPriority(
                            rank=1,
                            severity="high",
                            category="followup",
                            title=f"Follow up with {client.full_name}",
                            description=(
                                f"The last conversation was {days_since_contact} days ago."
                            ),
                            href=f"/clients/{client.id}",
                        ),
                    )
                )

        ordered = [
            priority
            for _, priority in sorted(
                priorities,
                key=lambda item: item[0],
                reverse=True,
            )[:5]
        ]
        return [priority.model_copy(update={"rank": rank}) for rank, priority in enumerate(ordered, 1)]

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
        priorities = self._build_priorities(overview.failed, clients)

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
            priorities=priorities,
            alerts=alerts,
            followups=followups,
        )
