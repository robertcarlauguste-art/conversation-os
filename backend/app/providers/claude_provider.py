"""
Claude-backed AIProvider (first concrete implementation, Sprint 2).

Business logic (memory/service.py) depends only on `AIProvider` —
this class is the one place that knows about the `anthropic` SDK.
Swapping to a different model provider later means adding a new
class here, not touching the memory slice.

Verification note: this class is exercised by real unit tests only up
to the point of constructing the request. The actual outbound call to
api.anthropic.com is not exercised in this project's automated tests
or in the sandbox this was built in — there's no ANTHROPIC_API_KEY
configured here, and tests use `FakeAIProvider` (see
memory/tests/conftest.py) so they stay fast, deterministic, and free.
Smoke-test this class against a real key before relying on it in
production.
"""

import anthropic

from app.providers.ai_provider import AICompletionResult, AIMessage, AIProvider


class ClaudeProvider(AIProvider):
    def __init__(self, api_key: str, model: str, timeout_seconds: float = 60.0) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout_seconds)
        self._model = model

    async def complete(self, messages: list[AIMessage], **kwargs) -> AICompletionResult:
        system_prompt = kwargs.pop("system", None)
        max_tokens = kwargs.pop("max_tokens", 2048)

        anthropic_messages: list[anthropic.types.MessageParam] = [
            {"role": "user" if m.role != "assistant" else "assistant", "content": m.content}
            for m in messages
        ]

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=anthropic_messages,
            **kwargs,
        )

        text_blocks = [block.text for block in response.content if block.type == "text"]
        return AICompletionResult(
            content="".join(text_blocks),
            model=response.model,
            raw=response.model_dump(),
        )
