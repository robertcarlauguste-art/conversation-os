"""
Transcription provider abstraction (Sprint 2).

Same shape as `AIProvider`: business logic (the transcription slice's
service.py) depends on `TranscriptionProvider`, never on a specific
vendor's SDK or HTTP API. This exists as a separate interface from
`AIProvider` rather than folded into it, because speech-to-text and
text completion are genuinely different capabilities with different
inputs (audio bytes vs. messages) — forcing them into one interface
would make both harder to use correctly.

Note on why this needs a real external vendor at all: Anthropic's API
does not transcribe audio (confirmed before implementing this) — the
standard pattern, including in Anthropic's own published examples, is
to transcribe with a dedicated speech-to-text vendor first, then send
the resulting text to Claude. `OpenAIWhisperProvider` is that first
step; `ClaudeProvider` (ai_provider) is the second.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    text: str
    language: str | None
    raw: dict | None = None


class TranscriptionProvider(ABC):
    """Abstract interface every concrete speech-to-text provider must implement."""

    @abstractmethod
    async def transcribe(self, *, audio_bytes: bytes, filename: str) -> TranscriptionResult:
        raise NotImplementedError
