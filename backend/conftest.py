import asyncio
import os
import selectors
import sys

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


def pytest_asyncio_loop_factories(config, item):
    """Create the event loop required by Psycopg async connections on Windows."""
    del config, item

    if sys.platform == "win32":
        return {
            "windows-selector": lambda: asyncio.SelectorEventLoop(
                selectors.SelectSelector()
            )
        }

    return {"default": asyncio.new_event_loop}
