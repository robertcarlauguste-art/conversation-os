"""
Alembic environment.

Think of migrations like a construction change-log for the database:
each file records one change (add a wall, move a door) so the schema
can be rebuilt from scratch or rolled back step by step. Sprint 0
only records the "empty lot survey" — no rooms (tables) built yet.
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import get_settings
from app.models.base import Base

# Import every domain's models so they register on Base.metadata.
# Add a line here whenever a new slice adds models.
from app.conversation import models as conversation_models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable: AsyncEngine = create_async_engine(config.get_main_option("sqlalchemy.url"))
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
