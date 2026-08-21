from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.schemas.envelope import ApiResponse

from .repository import OperationsRepository
from .schemas import OperationalStatus
from .service import OperationsService

router = APIRouter(prefix="/operations", tags=["operations"])


def get_operations_service(
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> OperationsService:
    return OperationsService(
        repository=OperationsRepository(session, principal.user_id),
        settings=settings,
    )


@router.get("", response_model=ApiResponse[OperationalStatus])
async def get_operational_status(
    service: OperationsService = Depends(get_operations_service),
) -> ApiResponse[OperationalStatus]:
    return ApiResponse(success=True, data=await service.get_status())
