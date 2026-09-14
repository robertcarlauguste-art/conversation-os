import asyncio

import boto3
import httpx
from botocore.config import Config
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.monitoring.repository import processing_counts


async def collect(settings: Settings, engine: AsyncEngine) -> dict[str, bool | None]:
    """True=incident, False=healthy, None=unknown/suppressed dependency."""
    signals: dict[str, bool | None] = {}

    async def api() -> None:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
                response = await client.get(
                    str(settings.monitoring_api_url).rstrip("/") + "/health"
                )
                signals["api_unavailable"] = (
                    response.status_code != 200 or response.json().get("status") != "ok"
                )
        except Exception:
            signals["api_unavailable"] = True

    async def database() -> None:
        try:
            async with asyncio.timeout(10):
                counts = await processing_counts(
                    engine,
                    max(900, settings.processing_job_timeout_seconds + 60),
                    settings.monitoring_failure_window_seconds,
                )
            signals.update(
                database_unavailable=False,
                processing_failed=counts["failed"] > 0,
                processing_stalled=counts["stalled"] > 0,
                repeated_provider_failures=(
                    counts["provider_failures"] >= settings.monitoring_provider_failure_threshold
                ),
            )
        except Exception:
            signals.update(
                database_unavailable=True,
                processing_failed=None,
                processing_stalled=None,
                repeated_provider_failures=None,
            )

    async def queue() -> None:
        if settings.processing_mode != "queue":
            signals.update(redis_unavailable=False, worker_unavailable=False, queue_backlog=False)
            return
        redis = Redis.from_url(settings.redis_url, socket_timeout=5, socket_connect_timeout=5)
        try:
            async with asyncio.timeout(10):
                await redis.ping()
                alive = await redis.exists("conversation-os:worker:health")
                depth = await redis.zcard("arq:queue")
            signals.update(
                redis_unavailable=False,
                worker_unavailable=not bool(alive),
                queue_backlog=depth >= settings.operations_queue_alert_threshold,
            )
        except Exception:
            signals.update(redis_unavailable=True, worker_unavailable=None, queue_backlog=None)
        finally:
            await redis.aclose()

    def storage_sync() -> bool:
        if settings.storage_backend != "s3":
            # A separate monitor cannot verify another service's local filesystem.
            return True
        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            config=Config(connect_timeout=5, read_timeout=5, retries={"max_attempts": 0}),
        )
        try:
            client.head_bucket(Bucket=settings.s3_bucket)
            return False
        finally:
            client.close()

    async def storage() -> None:
        try:
            signals["storage_unavailable"] = await asyncio.to_thread(storage_sync)
        except Exception:
            signals["storage_unavailable"] = True

    await asyncio.gather(api(), database(), queue(), storage())
    return signals
