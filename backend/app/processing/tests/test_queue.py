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


async def test_retry_queue_uses_fresh_identity_and_attempt_guard(monkeypatch):
    from app.processing.queue import enqueue_conversation_retry

    redis = AsyncMock()
    monkeypatch.setattr("app.processing.queue.create_pool", AsyncMock(return_value=redis))
    id_ = uuid4()
    settings = Settings(redis_url="redis://localhost:6379/0")
    await enqueue_conversation_retry(id_, "owner", settings, 3)
    await enqueue_conversation_retry(id_, "owner", settings, 3)
    calls = redis.enqueue_job.await_args_list
    assert calls[0].args == ("process_conversation", str(id_), "owner", 3)
    assert calls[0].kwargs["_job_id"] != calls[1].kwargs["_job_id"]


async def test_retry_queue_rejection_is_not_success(monkeypatch):
    import pytest

    from app.processing.queue import enqueue_conversation_retry

    redis = AsyncMock()
    redis.enqueue_job.return_value = None
    monkeypatch.setattr("app.processing.queue.create_pool", AsyncMock(return_value=redis))
    with pytest.raises(RuntimeError, match="Retry could not be queued"):
        await enqueue_conversation_retry(uuid4(), "owner", Settings(), 3)
    redis.aclose.assert_awaited_once()
