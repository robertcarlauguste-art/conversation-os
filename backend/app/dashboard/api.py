from fastapi import APIRouter, Depends

from app.client.api import get_client_service
from app.client.service import ClientService
from app.conversation.api import get_conversation_service
from app.conversation.service import ConversationService
from app.schemas.envelope import ApiResponse

from .schemas import DashboardResponse
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
) -> DashboardService:
    """
    Compose the dashboard service from existing domain services.

    FastAPI resolves each domain service's own dependencies,
    including database session, storage, and configuration.
    """

    return DashboardService(
        conversation_service=conversation_service,
        client_service=client_service,
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