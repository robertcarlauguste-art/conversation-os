import asyncio
import uuid

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.usage.service import LIMITS, UsageService


@pytest_asyncio.fixture
async def sessions():
    engine = create_async_engine(get_settings().database_url)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def test_concurrent_admission_is_durable_and_owner_scoped(sessions):
    owner = str(uuid.uuid4())

    async def request():
        async with sessions() as session:
            try:
                await UsageService(session, owner).consume_ai()
                return 200
            except HTTPException as exc:
                await session.rollback()
                return exc.status_code

    results = await asyncio.gather(*(request() for _ in range(12)))
    assert results.count(200) == 5
    assert results.count(429) == 7
    async with sessions() as session:
        assert (await UsageService(session, owner).snapshot())["remaining"]["ai"] == 0
        other = UsageService(session, str(uuid.uuid4()))
        assert (await other.snapshot())["remaining"]["ai"] == 5
        await other.consume_ai()


async def test_rollback_and_previous_day_do_not_consume_today(sessions):
    owner = str(uuid.uuid4())
    async with sessions() as session:
        usage = UsageService(session, owner)
        await usage.admit("uploads", size=100, seconds=180)
        await session.rollback()
        assert (await usage.snapshot())["remaining"]["uploads"] == 5
        await session.execute(
            text(
                "INSERT INTO pilot_usage(owner_id,day,uploads,ai,retries) "
                "VALUES(:owner,(clock_timestamp() AT TIME ZONE 'UTC')::date-1,5,5,2)"
            ),
            {"owner": owner},
        )
        await session.commit()
        assert (await usage.snapshot())["remaining"]["ai"] == 5
        for _ in range(2):
            await usage.admit("retries")
            await session.commit()
        with pytest.raises(HTTPException) as denied:
            await usage.admit("retries")
        assert denied.value.status_code == 429


async def test_upload_daily_and_storage_limits(sessions):
    owner = str(uuid.uuid4())
    async with sessions() as session:
        usage = UsageService(session, owner)
        with pytest.raises(HTTPException):
            await usage.admit("uploads", size=LIMITS["storage_bytes"] + 1, seconds=1)
        await session.rollback()
        for _ in range(5):
            await usage.admit("uploads", size=1, seconds=180)
            await session.commit()
        state = await usage.snapshot()
        assert state["used"]["audio_seconds"] == 900
        with pytest.raises(HTTPException):
            await usage.admit("uploads", size=1, seconds=1)


async def test_active_slots_and_deletion_preserve_daily_usage(sessions):
    from app.conversation.enums import ConversationSource, ConversationStatus
    from app.conversation.models import Conversation
    from app.conversation.repository import ConversationRepository

    owner = str(uuid.uuid4())
    async with sessions() as session:
        rows = [
            Conversation(
                owner_id=owner,
                filename="test.wav",
                storage_path="test",
                mime_type="audio/wav",
                file_size=10,
                status=ConversationStatus.COMPLETED,
                source=ConversationSource.UPLOAD,
            )
            for _ in range(30)
        ]
        session.add_all(rows)
        await session.commit()
        usage = UsageService(session, owner)
        await usage.consume_ai()
        with pytest.raises(HTTPException):
            await usage.admit("uploads", size=10, seconds=1)
        await session.rollback()
        row_id = await session.scalar(
            text("SELECT id FROM conversations WHERE owner_id=:owner LIMIT 1"), {"owner": owner}
        )
        await ConversationRepository(session, owner).delete_by_id(row_id)
        assert (await usage.snapshot())["remaining"]["recordings"] == 1
        assert (await usage.snapshot())["used"]["ai"] == 1
        await usage.admit("uploads", size=10, seconds=1)
        await session.rollback()
