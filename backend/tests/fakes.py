"""
Fake providers shared across test suites.

These implement the real `AIProvider`/`TranscriptionProvider`
interfaces so the real orchestrator, real services, and real
repositories can all run in tests exactly as they would in
production — only the external network call is faked. This is the
same dependency-injection seam `conversation/tests` already used for
`StorageBackend` in Sprint 1.
"""

from app.providers.ai_provider import AICompletionResult, AIMessage, AIProvider
from app.providers.transcription_provider import TranscriptionProvider, TranscriptionResult

FAKE_EXTRACTION_JSON = """{
  "summary": "The buyer and agent discussed offer terms and next steps.",
  "decisions": ["Offer at asking price with a 30-day close"],
  "action_items": [
    {
      "task": "Send updated pre-approval letter",
      "due": null,
      "assignee": "Sam Agent"
    },
    {
      "task": "Schedule inspection",
      "due": null,
      "assignee": "Sam Agent"
    }
  ],
  "people": [
    {
      "name": "Jane Buyer",
      "role": "buyer",
      "entity_type": "CLIENT"
    },
    {
      "name": "Sam Agent",
      "role": "agent",
      "entity_type": "AGENT"
    }
  ],
  "topics": ["financing", "offer terms", "timeline"],
  "confidence": 0.87
}"""


class FakeAIProvider(AIProvider):
    def __init__(
        self, response_json: str = FAKE_EXTRACTION_JSON, model: str = "fake-claude"
    ) -> None:
        self._response_json = response_json
        self._model = model

    async def complete(self, messages: list[AIMessage], **kwargs) -> AICompletionResult:
        return AICompletionResult(content=self._response_json, model=self._model)


class FakeTranscriptionProvider(TranscriptionProvider):
    def __init__(self, text: str = "This is a fake transcript for testing.") -> None:
        self._text = text

    async def transcribe(self, *, audio_bytes: bytes, filename: str) -> TranscriptionResult:
        return TranscriptionResult(text=self._text, language="en")
