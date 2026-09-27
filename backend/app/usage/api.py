from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.schemas.envelope import ApiResponse
from app.usage.service import UsageService

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("")
async def get_usage(
    principal: CurrentPrincipal,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    if not settings.pilot_limits_enabled:
        return ApiResponse(success=True, data={"enabled": False})
    return ApiResponse(success=True, data=await UsageService(session, principal.user_id).snapshot())
