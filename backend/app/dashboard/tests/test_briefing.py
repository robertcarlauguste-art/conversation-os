from datetime import UTC, datetime

from app.dashboard.briefing import DashboardBriefingService
from app.dashboard.schemas import (
    DashboardBriefItem,
    DashboardOverview,
    DashboardPriority,
    DashboardResponse,
)
from app.providers.ai_provider import AICompletionResult, AIMessage, AIProvider

NOW = datetime(2026, 8, 17, 12, tzinfo=UTC)


def _dashboard_response() -> DashboardResponse:
    return DashboardResponse(
        overview=DashboardOverview(
            clients=1,
            conversations=22,
            completed=9,
            processing=0,
            failed=13,
        ),
        recent_clients=[],
        recent_conversations=[],
        daily_brief=[
            DashboardBriefItem(
                category="conversations",
                text="22 conversations stored.",
                tone="neutral",
            ),
            DashboardBriefItem(
                category="attention",
                text="13 require attention.",
                tone="warning",
            ),
        ],
        priorities=[
            DashboardPriority(
                rank=1,
                severity="critical",
                category="processing",
                title="Review 13 failed conversations",
                description="Resolve processing failures.",
                href="/conversations",
            )
        ],
        client_recommendations=[],
        next_actions=[],
        recent_activity=[],
        alerts=[],
        followups=[],
    )


class StubDashboardService:
    async def get_dashboard(self) -> DashboardResponse:
        return _dashboard_response()


class StubAIProvider(AIProvider):
    def __init__(self, *, fail: bool = False, content: str | None = None) -> None:
        self.fail = fail
        self.content = content
        self.messages: list[AIMessage] = []

    async def complete(
        self,
        messages: list[AIMessage],
        **kwargs,
    ) -> AICompletionResult:
        self.messages = messages
        if self.fail:
            raise RuntimeError("provider unavailable")
        return AICompletionResult(
            content=self.content or " Review failed conversations first. ",
            model="test-model",
        )


def _service(provider: AIProvider | None) -> DashboardBriefingService:
    return DashboardBriefingService(
        StubDashboardService(),
        provider,
        model="test-model",
        clock=lambda: NOW,
    )


async def test_generates_grounded_ai_briefing() -> None:
    provider = StubAIProvider()

    briefing = await _service(provider).generate()

    assert briefing.content == "Review failed conversations first."
    assert briefing.source == "ai"
    assert briefing.model == "test-model"
    assert briefing.fallback_reason is None
    assert "Review 13 failed conversations" in provider.messages[0].content
    assert "Do not invent" in provider.messages[0].content


async def test_falls_back_when_ai_is_not_configured() -> None:
    briefing = await _service(None).generate()

    assert briefing.source == "deterministic"
    assert briefing.fallback_reason == "not_configured"
    assert "22 conversations stored." in briefing.content
    assert "Review 13 failed conversations" in briefing.content


async def test_falls_back_when_provider_fails() -> None:
    briefing = await _service(StubAIProvider(fail=True)).generate()

    assert briefing.source == "deterministic"
    assert briefing.fallback_reason == "provider_error"
    assert briefing.generated_at == NOW


async def test_falls_back_when_provider_returns_empty_content() -> None:
    briefing = await _service(StubAIProvider(content="   ")).generate()

    assert briefing.source == "deterministic"
    assert briefing.fallback_reason == "provider_error"
    assert "Review 13 failed conversations" in briefing.content
