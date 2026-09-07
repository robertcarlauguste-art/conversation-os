import uuid

from arq.connections import RedisSettings, create_pool

from app.core.config import Settings


async def enqueue_conversation_processing(
    conversation_id: uuid.UUID,
    owner_id: str,
    settings: Settings,
) -> None:
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        await redis.enqueue_job(
            "process_conversation",
            str(conversation_id),
            owner_id,
            _job_id=f"conversation:{conversation_id}",
        )
    finally:
        await redis.aclose()


async def enqueue_conversation_retry(
    conversation_id: uuid.UUID, owner_id: str, settings: Settings, attempts: int
) -> None:
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        job = await redis.enqueue_job(
            "process_conversation",
            str(conversation_id),
            owner_id,
            attempts,
            _job_id=f"conversation:{conversation_id}:retry:{uuid.uuid4()}",
        )
        if job is None:
            raise RuntimeError("Retry could not be queued.")
    finally:
        await redis.aclose()
