import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.api import get_client_service
from app.client.service import ClientService
from app.conversation.api import get_conversation_service
from app.conversation.service import ConversationService
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.providers.ai_provider import AIProvider
from app.providers.dependencies import get_ai_provider
from app.schemas.envelope import ApiResponse

from .briefing import DashboardBriefingService
from .repository import DashboardRepository
from .schemas import (
    DashboardAIBriefing,
    DashboardResponse,
    FollowupActionRequest,
    FollowupActionResult,
)
from .service import DashboardService


router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
)


def get_dashboard_service(
    conversation_service: ConversationService = Depends(
        get_conversation_service
    ),
    client_service: ClientService = Depends(
        get_client_service
    ),
    session: AsyncSession = Depends(get_db_session),
) -> DashboardService:
    """
    Compose the dashboard service from existing domain services.

    FastAPI resolves each domain service's own dependencies,
    including database session, storage, and configuration.
    """

    return DashboardService(
        conversation_service=conversation_service,
        client_service=client_service,
        repository=DashboardRepository(session),
    )


def get_dashboard_briefing_service(
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    settings: Settings = Depends(get_settings),
) -> DashboardBriefingService:
    provider: AIProvider | None = None
    if settings.anthropic_api_key:
        provider = get_ai_provider(settings)

    return DashboardBriefingService(
        dashboard_service,
        provider,
        model=settings.anthropic_model,
    )


@router.get(
    "",
    response_model=ApiResponse[DashboardResponse],
)
async def get_dashboard(
    service: DashboardService = Depends(get_dashboard_service),
) -> ApiResponse[DashboardResponse]:

    dashboard = await service.get_dashboard()

    return ApiResponse(
        success=True,
        data=dashboard,
    )


@router.post(
    "/briefing",
    response_model=ApiResponse[DashboardAIBriefing],
)
async def generate_dashboard_briefing(
    service: DashboardBriefingService = Depends(get_dashboard_briefing_service),
) -> ApiResponse[DashboardAIBriefing]:
    briefing = await service.generate()
    return ApiResponse(success=True, data=briefing)


@router.post(
    "/recommendations/{client_id}/actions",
    response_model=ApiResponse[FollowupActionResult],
)
async def record_followup_action(
    client_id: uuid.UUID,
    request: FollowupActionRequest,
    service: DashboardService = Depends(get_dashboard_service),
) -> ApiResponse[FollowupActionResult]:
    result = await service.record_followup_action(client_id, request)
    return ApiResponse(success=True, data=result)
