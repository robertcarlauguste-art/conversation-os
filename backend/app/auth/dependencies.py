from typing import Annotated

from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from fastapi import Depends, HTTPException, Request, status

from app.auth.schemas import Principal
from app.core.config import Settings, get_settings


def require_principal(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal:
    """Resolve the authenticated actor without leaking Clerk into domain slices."""
    if not settings.auth_enabled:
        principal = Principal(
            user_id=settings.auth_dev_user_id,
            is_development_identity=True,
        )
        if hasattr(request, "state"):
            request.state.user_id = principal.user_id
        return principal

    state = Clerk(bearer_auth=settings.clerk_secret_key).authenticate_request(
        request,
        AuthenticateRequestOptions(
            secret_key=settings.clerk_secret_key,
            jwt_key=settings.clerk_jwt_key,
            authorized_parties=list(settings.clerk_authorized_parties),
        ),
    )
    if not state.is_authenticated or not state.payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = state.payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated token has no user identity.",
        )

    organization_id = state.payload.get("org_id")
    principal = Principal(
        user_id=user_id,
        organization_id=organization_id if isinstance(organization_id, str) else None,
    )
    if hasattr(request, "state"):
        request.state.user_id = principal.user_id
    return principal


CurrentPrincipal = Annotated[Principal, Depends(require_principal)]
