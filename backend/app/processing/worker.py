import uuid
from typing import Any

from arq.connections import RedisSettings
from arq.worker import Retry

from app.conversation.storage_factory import build_storage_backend
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.orchestrator.dependencies import build_conversation_processing_orchestrator


async def process_conversation(
    _ctx: dict[str, Any],
    conversation_id: str,
    owner_id: str,
) -> None:
    settings = get_settings()
    storage = build_storage_backend(settings)
    async with AsyncSessionLocal() as session:
        orchestrator = build_conversation_processing_orchestrator(
            session,
            storage,
            settings,
            owner_id,
        )
        try:
            await orchestrator.run(uuid.UUID(conversation_id))
        except Exception as exc:
            # SQLAlchemy sessions remain unusable after many database errors until
            # explicitly rolled back. Recover before ARQ reuses the connection or
            # before terminal failure is written with this session.
            await session.rollback()

            job_try = int(_ctx.get("job_try", 1))
            if job_try < settings.processing_max_tries:
                raise Retry(defer=job_try * 5) from exc

            await orchestrator.mark_failed(uuid.UUID(conversation_id), str(exc))
            raise


settings = get_settings()


class WorkerSettings:
    functions = [process_conversation]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_tries = settings.processing_max_tries
    job_timeout = settings.processing_job_timeout_seconds
    health_check_interval = 30
    health_check_key = "conversation-os:worker:health"
