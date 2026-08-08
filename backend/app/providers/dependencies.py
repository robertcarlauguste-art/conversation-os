"""
Provider factories.

FastAPI dependency functions that construct concrete providers from
settings. Lives in `app/providers/` (shared infrastructure) rather
than being duplicated in every slice that needs an AIProvider or
TranscriptionProvider — currently that's just the orchestrator's
wiring in conversation/api.py, but any future slice needing either
provider reuses these instead of constructing its own.
"""

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.providers.ai_provider import AIProvider
from app.providers.claude_provider import ClaudeProvider
from app.providers.openai_whisper_provider import OpenAIWhisperProvider
from app.providers.transcription_provider import TranscriptionProvider


def get_ai_provider(settings: Settings = Depends(get_settings)) -> AIProvider:
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not configured. Set it in .env before uploading "
            "a conversation — Sprint 2's extraction pipeline requires it."
        )
    return ClaudeProvider(
        api_key=settings.anthropic_api_key,
        model=settings.anthropic_model,
        timeout_seconds=settings.ai_request_timeout_seconds,
    )


def get_transcription_provider(
    settings: Settings = Depends(get_settings),
) -> TranscriptionProvider:
    if not settings.openai_api_key:
        from app.providers.noop_transcription_provider import (
            NoOpTranscriptionProvider,
        )

        return NoOpTranscriptionProvider()

    return OpenAIWhisperProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_whisper_model,
        timeout_seconds=settings.ai_request_timeout_seconds,
    )