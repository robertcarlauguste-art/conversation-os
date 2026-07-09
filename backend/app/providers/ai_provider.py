"""
AI Provider abstraction (Rule 6).

Picture a universal power adapter: business logic plugs into
`AIProvider`, and it doesn't care whether the wall socket behind it is
OpenAI, Claude, or Gemini. Swapping providers means swapping the
adapter, not rewiring the whole house.

Sprint 0 scope: define the interface only. No HTTP calls, no SDKs,
no API keys used yet — that's explicitly out of scope until a future
sprint actually needs to talk to a model.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AIMessage:
    role: str
    content: str


@dataclass
class AICompletionResult:
    content: str
    model: str
    raw: dict | None = None


class AIProvider(ABC):
    """Abstract interface every concrete AI provider must implement."""

    @abstractmethod
    async def complete(self, messages: list[AIMessage], **kwargs) -> AICompletionResult:
        """Send messages to the underlying model and return a normalized result."""
        raise NotImplementedError


class NotImplementedProvider(AIProvider):
    """
    Placeholder provider so the abstraction is wired up end-to-end
    without committing to a vendor SDK in Sprint 0.
    """

    async def complete(self, messages: list[AIMessage], **kwargs) -> AICompletionResult:
        raise NotImplementedError(
            "AI providers are out of scope for Sprint 0. "
            "Implement OpenAIProvider / ClaudeProvider / GeminiProvider in a future sprint."
        )
