import tempfile
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.conversation.storage import LocalStorageBackend
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


@pytest.fixture
def storage_backend() -> Generator[LocalStorageBackend]:
    with tempfile.TemporaryDirectory() as tmp:
        yield LocalStorageBackend(root=tmp)
