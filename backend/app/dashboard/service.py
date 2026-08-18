import uuid
from datetime import datetime, timedelta, timezone
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
    FollowupActionRequest,
    FollowupActionResult,
)
from .models import ClientFollowupAction, FollowupAction
from .repository import DashboardRepository


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
        repository: DashboardRepository | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._conversations = conversation_service
        self._clients = client_service
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def _build_alerts(failed: int) -> list[str]:
        if failed == 0:
            return []

        if failed == 1:
            return ["1 conversation failed processing and needs review."]

        return [f"{failed} conversations failed processing and need review."]

    @staticmethod
    def _followup_state(
        client: Client,
        latest_action: ClientFollowupAction | None,
        now: datetime,
    ) -> tuple[bool, datetime | None]:
        latest_contact = (
            max(
                conversation.created_at
                for conversation in client.conversations
            )
            if client.conversations
            else None
        )
        if latest_action is None:
            return False, latest_contact
        if (
            latest_action.action == FollowupAction.SNOOZE
            and latest_action.snoozed_until is not None
            and latest_action.snoozed_until > now
        ):
            return True, latest_contact
        if latest_action.action == FollowupAction.RECORD_CONTACT:
            if (
                latest_contact is None
                or latest_action.created_at > latest_contact
            ):
                latest_contact = latest_action.created_at
        if (
            latest_action.action == FollowupAction.COMPLETE
            and (
                latest_contact is None
                or latest_contact <= latest_action.created_at
            )
        ):
            return True, latest_contact
        return False, latest_contact

    def _build_followups(
        self,
        clients: list[Client],
        latest_actions: dict[uuid.UUID, ClientFollowupAction] | None = None,
    ) -> list[str]:
        now = self._clock()
        followups: list[str] = []
        latest_actions = latest_actions or {}

        for client in clients:
            suppressed, latest = self._followup_state(
                client, latest_actions.get(client.id), now
            )
            if suppressed:
                continue
            if latest is None:
                followups.append(
                    f"Schedule a first conversation with {client.full_name}."
                )
                continue
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
        latest_actions: dict[uuid.UUID, ClientFollowupAction] | None = None,
    ) -> list[DashboardPriority]:
        priorities: list[tuple[int, DashboardPriority]] = []
        latest_actions = latest_actions or {}

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
            suppressed, latest = self._followup_state(
                client, latest_actions.get(client.id), now
            )
            if suppressed:
                continue
            if latest is None:
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

    def _count_due_followups(
        self,
        clients: list[Client],
        latest_actions: dict[uuid.UUID, ClientFollowupAction] | None = None,
    ) -> int:
        now = self._clock()
        due = 0
        latest_actions = latest_actions or {}

        for client in clients:
            suppressed, latest = self._followup_state(
                client, latest_actions.get(client.id), now
            )
            if suppressed:
                continue
            if latest is None:
                due += 1
                continue
            if (now - latest).days >= self.FOLLOWUP_AFTER_DAYS:
                due += 1

        return due

    def _build_client_recommendations(
        self,
        clients: list[Client],
        latest_actions: dict[uuid.UUID, ClientFollowupAction] | None = None,
    ) -> list[DashboardClientRecommendation]:
        """Rank grounded client actions by follow-up urgency."""
        now = self._clock()
        recommendations: list[DashboardClientRecommendation] = []
        latest_actions = latest_actions or {}

        for client in clients:
            latest_action = latest_actions.get(client.id)
            conversation_count = len(client.conversations)
            suppressed, latest_conversation = self._followup_state(
                client, latest_action, now
            )
            if suppressed:
                continue

            if latest_conversation is None:
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

            days_since_contact = max(0, (now - latest_conversation).days)
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

    async def record_followup_action(
        self,
        client_id: uuid.UUID,
        request: FollowupActionRequest,
    ) -> FollowupActionResult:
        if self._repository is None:
            raise RuntimeError("Dashboard repository is required for actions")

        await self._clients.get_profile(client_id)
        now = self._clock()
        action = FollowupAction(request.action.upper())
        snoozed_until = (
            now + timedelta(days=request.snooze_days)
            if request.snooze_days is not None
            else None
        )
        saved = await self._repository.add_followup_action(
            ClientFollowupAction(
                client_id=client_id,
                action=action,
                snoozed_until=snoozed_until,
                created_at=now,
            )
        )
        return FollowupActionResult(
            client_id=client_id,
            action=request.action,
            snoozed_until=saved.snoozed_until,
            recorded_at=saved.created_at,
        )

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
        latest_actions = (
            await self._repository.list_latest_followup_actions()
            if self._repository is not None
            else {}
        )

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
        followups = self._build_followups(clients, latest_actions)
        priorities = self._build_priorities(
            overview.failed, clients, latest_actions
        )
        client_recommendations = self._build_client_recommendations(
            clients,
            latest_actions,
        )
        daily_brief = self._build_daily_brief(
            overview,
            self._count_due_followups(clients, latest_actions),
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
