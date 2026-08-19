"""
No-op transcription provider.

Used during development when no transcription API key is configured.
Allows uploads and application testing without external AI services.
"""

from app.providers.transcription_provider import (
    TranscriptionProvider,
    TranscriptionResult,
)


class NoOpTranscriptionProvider(TranscriptionProvider):
    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        filename: str,
    ) -> TranscriptionResult:
        return TranscriptionResult(
            text="",
            language=None,
            raw={
                "provider": "noop",
                "message": "Transcription skipped. OPENAI_API_KEY not configured.",
                "filename": filename,
            },
        )
