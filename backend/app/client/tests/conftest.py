from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_client_tables(db_session: AsyncSession) -> AsyncGenerator[None]:
    """
    ClientService.find_or_create/record_facts call commit()
    internally (matching the rest of the codebase's service pattern),
    so data written mid-test is NOT undone by db_session's rollback()
    at teardown — commit() finalizes it. Without this, "Jane Smith" /
    "buyer" created in one test collides with the next test's
    assumption of a clean slate. Truncating before each test (not
    after) means a failed test's leftover data doesn't cascade into
    the next one either.
    """
    await db_session.execute(text("TRUNCATE TABLE client_facts, clients CASCADE"))
    await db_session.commit()
    yield
