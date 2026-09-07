import uuid
from typing import Any

from arq.connections import RedisSettings
from arq.worker import Retry

from app.conversation.enums import ConversationStatus
from app.conversation.repository import ConversationRepository
from app.conversation.storage_factory import build_storage_backend
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.orchestrator.dependencies import build_conversation_processing_orchestrator
from app.processing.visibility import safe_error


async def process_conversation(
    _ctx: dict[str, Any],
    conversation_id: str,
    owner_id: str,
    retry_attempts: int | None = None,
) -> None:
    # ARQ logs raised exceptions. Contain setup, rollback and terminal-write failures too.
    try:
        await _process_conversation(_ctx, conversation_id, owner_id, retry_attempts)
    except Retry:
        raise
    except Exception as exc:
        raise RuntimeError(safe_error(str(exc))) from None


async def _process_conversation(
    _ctx: dict[str, Any],
    conversation_id: str,
    owner_id: str,
    retry_attempts: int | None = None,
) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        # The API holds this row lock until queue dispatch commits or rolls back.
        # Keep it until start_processing_attempt commits the increment: only one
        # first delivery can consume this attempt baseline, even after ambiguous dispatch.
        if retry_attempts is not None and int(_ctx.get("job_try", 1)) == 1:
            conversation = await ConversationRepository(session, owner_id).get_for_retry(
                uuid.UUID(conversation_id)
            )
            if (
                conversation is None
                or conversation.status != ConversationStatus.QUEUED
                or conversation.processing_attempts != retry_attempts
            ):
                return
        orchestrator = None
        try:
            storage = build_storage_backend(settings)
            orchestrator = build_conversation_processing_orchestrator(
                session,
                storage,
                settings,
                owner_id,
            )
            await orchestrator.run(uuid.UUID(conversation_id), terminal_failure=False)
        except Exception as exc:
            if orchestrator is None:
                # Configuration/setup failures cannot start a processing attempt.
                # Preserve the first-delivery lock while making failure terminal.
                await ConversationRepository(session, owner_id).mark_processing_failed(
                    uuid.UUID(conversation_id), safe_error(str(exc)) or "Processing failed."
                )
                raise RuntimeError(safe_error(str(exc))) from None
            # SQLAlchemy sessions remain unusable after many database errors until
            # explicitly rolled back. Recover before ARQ reuses the connection or
            # before terminal failure is written with this session.
            await session.rollback()

            job_try = int(_ctx.get("job_try", 1))
            if job_try < settings.processing_max_tries:
                raise Retry(defer=job_try * 5) from None

            await orchestrator.mark_failed(
                uuid.UUID(conversation_id), safe_error(str(exc)) or "Processing failed."
            )
            raise RuntimeError(safe_error(str(exc))) from None


settings = get_settings()


class WorkerSettings:
    functions = [process_conversation]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_tries = settings.processing_max_tries
    job_timeout = settings.processing_job_timeout_seconds
    health_check_interval = 30
    health_check_key = "conversation-os:worker:health"
