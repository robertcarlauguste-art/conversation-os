"""
Base orchestrator.

Some workflows (e.g. Sprint 1's Conversation → Transcript → Knowledge
→ Actions → Timeline → Communication pipeline) span more than one
service. An orchestrator is the "conductor" for that: it calls
services in the right order and passes results between them, but it
still doesn't own business rules itself — each step's logic lives in
that step's own service (Rule 3). This keeps a single service from
having to know about every other domain just to kick off a workflow.

This is a scaffold only, matching every other new package added this
sprint: no concrete orchestration exists yet, since Sprint 0 adds no
business features. A concrete orchestrator (e.g. a future
`ConversationPipelineOrchestrator`) will subclass `BaseOrchestrator`
in Sprint 1.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseOrchestrator(ABC):
    """Coordinates a multi-step workflow across one or more services."""

    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the workflow's steps in order. Implemented per concrete orchestrator."""
        raise NotImplementedError
