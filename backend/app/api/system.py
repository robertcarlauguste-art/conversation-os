"""
Rule 1: business logic must never live in routes. These two endpoints
have no business logic to hide — they're the building's front-door
buzzer, confirming someone's home and reading the address plaque.
"""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok"}


@router.get("/version", tags=["system"])
async def version() -> dict:
    settings = get_settings()
    return {"app_name": settings.app_name, "version": settings.version, "env": settings.app_env}
