from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings


@dataclass(frozen=True)
class ReadinessResult:
    ready: bool
    checks: dict[str, str]


async def check_readiness(settings: Settings, engine: AsyncEngine) -> ReadinessResult:
    checks: dict[str, str] = {}
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"

    if settings.processing_mode == "queue":
        redis = Redis.from_url(settings.redis_url)
        try:
            await redis.ping()
            checks["redis"] = "ok"
            worker_alive = await redis.exists("conversation-os:worker:health")
            checks["worker"] = "ok" if worker_alive else "unavailable"
        except Exception:
            checks["redis"] = "unavailable"
            checks["worker"] = "unavailable"
        finally:
            await redis.aclose()

    return ReadinessResult(
        ready=all(value == "ok" for value in checks.values()),
        checks=checks,
    )
