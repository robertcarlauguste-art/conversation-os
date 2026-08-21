from unittest.mock import AsyncMock
from uuid import uuid4

from app.core.config import Settings
from app.processing.queue import enqueue_conversation_processing


async def test_enqueue_uses_unique_conversation_job_id(monkeypatch) -> None:
    redis = AsyncMock()

    async def fake_create_pool(_settings):
        return redis

    monkeypatch.setattr("app.processing.queue.create_pool", fake_create_pool)
    conversation_id = uuid4()

    await enqueue_conversation_processing(
        conversation_id,
        "user_123",
        Settings(redis_url="redis://localhost:6379/0"),
    )

    redis.enqueue_job.assert_awaited_once_with(
        "process_conversation",
        str(conversation_id),
        "user_123",
        _job_id=f"conversation:{conversation_id}",
    )
    redis.aclose.assert_awaited_once()
