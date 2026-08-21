"""
Application entrypoint.

This file's only job is assembly: wire the middleware, mount the
router, and hand back the app object. Like a stage manager on
opening night — it doesn't act in the play, it just makes sure
everyone is in position before the curtain rises.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import RequestLoggingMiddleware, configure_logging

configure_logging()
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="ConversationOS - AI-powered relationship intelligence platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(api_router)
