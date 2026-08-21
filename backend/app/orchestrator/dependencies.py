"""
Orchestrator construction.

Deliberately NOT a FastAPI `Depends()` chain — the underlying provider
factories (`get_ai_provider`, `get_transcription_provider`) raise a
clear `RuntimeError` if an API key isn't configured, and if that
raised during FastAPI's dependency-resolution phase (i.e. if the
orchestrator were itself injected via `Depends(...)` as an endpoint
parameter), it would happen *before* the endpoint body runs — meaning
a missing API key would block the upload itself, not just processing.
Building the orchestrator as a plain function call inside the
endpoint body (see conversation/api.py) means upload failures and
processing failures can be handled separately, which is the behavior
the spec's "upload workflow" and "processing" are meant to have.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.client.repository import ClientRepository
from app.client.service import ClientService
from app.conversation.repository import ConversationRepository
from app.conversation.service import ConversationService
from app.conversation.storage import StorageBackend
from app.core.config import Settings
from app.memory.repository import MemoryRepository
from app.memory.service import MemoryService
from app.orchestrator.conversation_processing import ConversationProcessingOrchestrator
from app.providers.dependencies import get_ai_provider, get_transcription_provider
from app.transcription.repository import TranscriptRepository
from app.transcription.service import TranscriptionService


def build_conversation_processing_orchestrator(
    session: AsyncSession,
    storage: StorageBackend,
    settings: Settings,
    owner_id: str = "dev_user",
) -> ConversationProcessingOrchestrator:
    conversation_service = ConversationService(
        ConversationRepository(session, owner_id),
        storage,
        allowed_mime_types=settings.allowed_audio_mime_types,
        max_upload_size_bytes=settings.max_upload_size_bytes,
    )
    transcription_service = TranscriptionService(
        TranscriptRepository(session, owner_id),
        get_transcription_provider(settings),
        storage,
    )
    memory_service = MemoryService(
        MemoryRepository(session, owner_id),
        get_ai_provider(settings),
        model=settings.anthropic_model,
    )
    client_service = ClientService(ClientRepository(session, owner_id))
    return ConversationProcessingOrchestrator(
        conversation_service, transcription_service, memory_service, client_service
    )
