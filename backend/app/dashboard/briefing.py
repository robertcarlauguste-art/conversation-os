import json
import logging
from datetime import datetime, timezone
from typing import Callable

from app.providers.ai_provider import AIMessage, AIProvider

from .schemas import DashboardAIBriefing, DashboardResponse
from .service import DashboardService


logger = logging.getLogger("conversation_os.dashboard.briefing")


class DashboardBriefingService:
    """Synthesizes deterministic dashboard facts into concise briefing copy."""

    def __init__(
        self,
        dashboard_service: DashboardService,
        ai_provider: AIProvider | None,
        *,
        model: str | None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._dashboard = dashboard_service
        self._ai = ai_provider
        self._model = model
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def _fallback(dashboard: DashboardResponse) -> str:
        facts = " ".join(item.text for item in dashboard.daily_brief)
        if dashboard.priorities:
            return (
                f"{facts} Start with this priority: "
                f"{dashboard.priorities[0].title}."
            )
        return f"{facts} No priority actions require attention right now."

    @staticmethod
    def _prompt(dashboard: DashboardResponse) -> str:
        payload = {
            "daily_brief": [
                item.model_dump(mode="json") for item in dashboard.daily_brief
            ],
            "priorities": [
                item.model_dump(mode="json") for item in dashboard.priorities
            ],
            "client_recommendations": [
                item.model_dump(mode="json")
                for item in dashboard.client_recommendations
            ],
            "next_actions": [
                item.model_dump(mode="json")
                for item in dashboard.next_actions
            ],
        }
        return (
            "Write a concise morning executive briefing from this JSON data. "
            "Use no more than 90 words. State what happened, what needs attention, "
            "and the first recommended action. Do not invent facts, clients, dates, "
            "appointments, probabilities, or recommendations not supported by the data.\n\n"
            f"{json.dumps(payload)}"
        )

    async def generate(self) -> DashboardAIBriefing:
        dashboard = await self._dashboard.get_dashboard()
        generated_at = self._clock()

        if self._ai is None:
            return DashboardAIBriefing(
                content=self._fallback(dashboard),
                source="deterministic",
                fallback_reason="not_configured",
                generated_at=generated_at,
            )

        try:
            result = await self._ai.complete(
                [AIMessage(role="user", content=self._prompt(dashboard))],
                system=(
                    "You are the ConversationOS executive briefing writer. "
                    "Be direct, practical, and strictly grounded in supplied data."
                ),
                max_tokens=180,
            )
        except Exception:
            logger.warning("dashboard_ai_briefing_failed", exc_info=True)
            return DashboardAIBriefing(
                content=self._fallback(dashboard),
                source="deterministic",
                fallback_reason="provider_error",
                generated_at=generated_at,
            )

        content = result.content.strip()
        if not content:
            return DashboardAIBriefing(
                content=self._fallback(dashboard),
                source="deterministic",
                fallback_reason="provider_error",
                generated_at=generated_at,
            )

        return DashboardAIBriefing(
            content=content,
            source="ai",
            model=result.model or self._model,
            generated_at=generated_at,
        )
