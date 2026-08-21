"""
Rule 1: business logic must never live in routes. These two endpoints
have no business logic to hide — they're the building's front-door
buzzer, confirming someone's home and reading the address plaque.
"""

from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.core.database import engine
from app.core.health import check_readiness

router = APIRouter()


@router.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready", tags=["system"])
async def ready(response: Response) -> dict:
    result = await check_readiness(get_settings(), engine)
    if not result.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if result.ready else "not_ready",
        "checks": result.checks,
    }


@router.get("/version", tags=["system"])
async def version() -> dict:
    settings = get_settings()
    return {"app_name": settings.app_name, "version": settings.version, "env": settings.app_env}
