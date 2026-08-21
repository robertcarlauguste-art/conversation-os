from fastapi import APIRouter

from app.auth.dependencies import CurrentPrincipal
from app.auth.schemas import PrincipalResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=PrincipalResponse)
def get_current_identity(principal: CurrentPrincipal) -> PrincipalResponse:
    return PrincipalResponse(data=principal)
