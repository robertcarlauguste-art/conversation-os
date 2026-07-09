"""
API composition root.

Per ADR-004 (Vertical Slice Architecture, superseding ADR-002's
routing section): each slice owns its own routes (e.g.
`app/conversation/api.py`). This module's only job is to mount them
under the app — it contains no routes and no logic of its own, so
Rule 1 ("business logic must never exist inside API routes") still
holds: this file isn't a route, it's the thing that assembles them.

Adding a new slice means one new `include_router` call here.
"""

from fastapi import APIRouter

from app.api.system import router as system_router
from app.conversation.api import router as conversation_router

api_router = APIRouter()

# System routes (/health, /version) stay unprefixed — operational
# endpoints, not business API surface.
api_router.include_router(system_router)

# Business API surface is versioned.
api_router.include_router(conversation_router, prefix="/api/v1")
