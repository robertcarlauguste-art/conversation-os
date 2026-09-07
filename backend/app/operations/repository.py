from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.enums import ConversationStatus
from app.conversation.models import Conversation
from app.processing.visibility import stale_threshold_seconds

from .schemas import ProcessingMetrics


class OperationsRepository:
    def __init__(self, session: AsyncSession, owner_id: str) -> None:
        self.session = session
        self.owner_id = owner_id

    async def processing_metrics(self, max_tries: int) -> ProcessingMetrics:
        duration = func.extract(
            "epoch",
            Conversation.processing_completed_at - Conversation.processing_started_at,
        )
        cutoff = datetime.now(UTC) - timedelta(seconds=stale_threshold_seconds())
        stale = (
            (Conversation.status == ConversationStatus.QUEUED) & (Conversation.created_at < cutoff)
        ) | (
            (Conversation.status == ConversationStatus.PROCESSING)
            & (func.coalesce(Conversation.processing_started_at, Conversation.created_at) < cutoff)
        )
        result = await self.session.execute(
            select(
                func.count(Conversation.id),
                func.sum(case((Conversation.status == ConversationStatus.QUEUED, 1), else_=0)),
                func.sum(case((Conversation.status == ConversationStatus.PROCESSING, 1), else_=0)),
                func.sum(case((Conversation.status == ConversationStatus.COMPLETED, 1), else_=0)),
                func.sum(case((Conversation.status == ConversationStatus.FAILED, 1), else_=0)),
                func.sum(
                    case(
                        (
                            (Conversation.status == ConversationStatus.FAILED)
                            & (Conversation.processing_attempts >= max_tries),
                            1,
                        ),
                        else_=0,
                    )
                ),
                func.avg(duration).filter(
                    Conversation.processing_started_at.is_not(None),
                    Conversation.processing_completed_at.is_not(None),
                ),
                func.sum(case((stale, 1), else_=0)),
            ).where(Conversation.owner_id == self.owner_id)
        )
        row = result.one()
        return ProcessingMetrics(
            stale=int(row[7] or 0),
            stale_threshold_seconds=stale_threshold_seconds(),
            total=int(row[0] or 0),
            queued=int(row[1] or 0),
            processing=int(row[2] or 0),
            completed=int(row[3] or 0),
            failed=int(row[4] or 0),
            retry_exhausted=int(row[5] or 0),
            average_duration_seconds=round(float(row[6]), 2) if row[6] is not None else None,
        )
