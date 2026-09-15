"""Explicit operator aggregate access; never return rows or tenant identifiers."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def processing_counts(engine: AsyncEngine, stale_seconds: int, window: int) -> dict[str, int]:
    async with engine.connect() as connection:
        result = await connection.execute(
            text("""
                SELECT
                  count(*) FILTER (WHERE status = 'FAILED') AS failed,
                  count(*) FILTER (WHERE
                    (status = 'QUEUED' AND updated_at < now() - :stale * interval '1 second') OR
                    (status = 'PROCESSING' AND coalesce(processing_started_at, updated_at)
                      < now() - :stale * interval '1 second')) AS stalled,
                  count(*) FILTER (WHERE status IN ('FAILED', 'PROCESSING')
                    AND updated_at >= now() - :window * interval '1 second'
                    AND processing_error IN (:memory_error, :transcription_error))
                    AS provider_failures
                FROM conversations
            """),
            {
                "stale": stale_seconds,
                "window": window,
                "memory_error": (
                    "Memory extraction failed. Check the extraction provider configuration."
                ),
                "transcription_error": (
                    "Transcription failed. Check recording format and "
                    "transcription provider configuration."
                ),
            },
        )
        return {key: int(value) for key, value in result.mappings().one().items()}
