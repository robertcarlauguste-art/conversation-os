"""
Database engine and session factory.

This is the only file that knows how to open a "door" (connection) to
Postgres. Repositories (app/repositories/base.py and per-domain
repositories in future sprints) are the only code allowed to walk
through that door — API routes and services never touch it directly.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency that yields a session and always closes it."""
    async with AsyncSessionLocal() as session:
        yield session
