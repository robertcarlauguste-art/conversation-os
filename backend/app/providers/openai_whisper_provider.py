"""
OpenAI Whisper-backed TranscriptionProvider.

Verification note (read before trusting this in production): this
class was written and reviewed carefully, but could not be exercised
against the real `api.openai.com` endpoint in the environment this
was built in — that host isn't reachable from this sandbox's network,
and no OPENAI_API_KEY was configured here either. Automated tests use
`FakeTranscriptionProvider` instead (deterministic, no network, no
cost). Please smoke-test this against a real key and a real audio
file before relying on it.
"""

import httpx

from app.providers.transcription_provider import (
    TranscriptionProvider,
    TranscriptionResult,
)

WHISPER_ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"


class OpenAIWhisperProvider(TranscriptionProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        filename: str,
    ) -> TranscriptionResult:
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                WHISPER_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                },
                data={
                    "model": self._model,
                    "response_format": "verbose_json",
                },
                files={
                    "file": (filename, audio_bytes),
                },
            )

        # Parse the response body first so we can see the real OpenAI error.
        body = response.json()

        if response.status_code != 200:
            raise RuntimeError(f"OpenAI error {response.status_code}: {body}")

        return TranscriptionResult(
            text=body["text"],
            language=body.get("language"),
            raw=body,
        )
