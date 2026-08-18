from datetime import datetime, timezone
from typing import Callable

from app.client.models import Client
from app.client.schemas import ClientListItem
from app.client.service import ClientService
from app.conversation.enums import ConversationStatus
from app.conversation.schemas import ConversationListItem
from app.conversation.service import ConversationService

from .schemas import (
    DashboardBriefItem,
    DashboardClientRecommendation,
    DashboardOverview,
    DashboardPriority,
    DashboardResponse,
)


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

    def _count_due_followups(self, clients: list[Client]) -> int:
        now = self._clock()
        due = 0

        for client in clients:
            if not client.conversations:
                due += 1
                continue

            latest = max(
                conversation.created_at
                for conversation in client.conversations
            )
            if (now - latest).days >= self.FOLLOWUP_AFTER_DAYS:
                due += 1

        return due

    def _build_client_recommendations(
        self,
        clients: list[Client],
    ) -> list[DashboardClientRecommendation]:
        """Rank grounded client actions by follow-up urgency."""
        now = self._clock()
        recommendations: list[DashboardClientRecommendation] = []

        for client in clients:
            conversation_count = len(client.conversations)
            if conversation_count == 0:
                recommendations.append(
                    DashboardClientRecommendation(
                        rank=1,
                        client_id=client.id,
                        client_name=client.full_name,
                        urgency_score=50,
                        reason="No conversations are linked to this client yet.",
                        recommended_action="Schedule a first conversation.",
                        conversation_count=0,
                        href=f"/clients/{client.id}",
                    )
                )
                continue

            latest = max(
                conversation.created_at
                for conversation in client.conversations
            )
            days_since_contact = max(0, (now - latest).days)
            if days_since_contact < self.FOLLOWUP_AFTER_DAYS:
                continue

            recommendations.append(
                DashboardClientRecommendation(
                    rank=1,
                    client_id=client.id,
                    client_name=client.full_name,
                    urgency_score=min(100, 50 + days_since_contact),
                    reason=(
                        f"Last conversation was {days_since_contact} days ago."
                    ),
                    recommended_action="Follow up today.",
                    days_since_contact=days_since_contact,
                    conversation_count=conversation_count,
                    href=f"/clients/{client.id}",
                )
            )

        ordered = sorted(
            recommendations,
            key=lambda item: (
                -item.urgency_score,
                item.client_name.casefold(),
                str(item.client_id),
            ),
        )[:5]
        return [
            item.model_copy(update={"rank": rank})
            for rank, item in enumerate(ordered, 1)
        ]

    @staticmethod
    def _build_daily_brief(
        overview: DashboardOverview,
        due_followups: int,
    ) -> list[DashboardBriefItem]:
        conversation_noun = (
            "conversation" if overview.conversations == 1 else "conversations"
        )
        client_noun = "client" if overview.clients == 1 else "clients"
        followup_noun = "follow-up" if due_followups == 1 else "follow-ups"

        attention_text = (
            f"{overview.failed} require attention."
            if overview.failed
            else "No processing failures need attention."
        )
        followup_text = (
            f"{due_followups} {followup_noun} due."
            if due_followups
            else "No follow-ups are due."
        )

        return [
            DashboardBriefItem(
                category="conversations",
                text=f"{overview.conversations} {conversation_noun} stored.",
                tone="neutral",
            ),
            DashboardBriefItem(
                category="processing",
                text=f"{overview.completed} successfully processed.",
                tone="positive",
            ),
            DashboardBriefItem(
                category="attention",
                text=attention_text,
                tone="warning" if overview.failed else "positive",
            ),
            DashboardBriefItem(
                category="clients",
                text=f"{overview.clients} {client_noun} tracked.",
                tone="neutral",
            ),
            DashboardBriefItem(
                category="followups",
                text=followup_text,
                tone="warning" if due_followups else "positive",
            ),
        ]

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
        client_recommendations = self._build_client_recommendations(clients)
        daily_brief = self._build_daily_brief(
            overview,
            self._count_due_followups(clients),
        )

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
            daily_brief=daily_brief,
            priorities=priorities,
            client_recommendations=client_recommendations,
            alerts=alerts,
            followups=followups,
        )
