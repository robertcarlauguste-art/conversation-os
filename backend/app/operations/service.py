from collections.abc import Callable
from datetime import UTC, datetime

from redis.asyncio import Redis

from app.core.config import Settings

from .repository import OperationsRepository
from .schemas import InfrastructureMetrics, OperationalAlert, OperationalStatus


class OperationsService:
    def __init__(
        self,
        repository: OperationsRepository,
        settings: Settings,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.settings = settings
        self.clock = clock or (lambda: datetime.now(UTC))

    async def get_status(self) -> OperationalStatus:
        processing = await self.repository.processing_metrics(self.settings.processing_max_tries)
        infrastructure = await self._infrastructure_metrics()
        return OperationalStatus(
            processing=processing,
            infrastructure=infrastructure,
            alerts=self._build_alerts(
                processing.failed, processing.retry_exhausted, infrastructure
            ),
            observed_at=self.clock(),
        )

    async def _infrastructure_metrics(self) -> InfrastructureMetrics:
        if self.settings.processing_mode == "inline":
            return InfrastructureMetrics(
                processing_mode="inline", queue_depth=None, worker_available=None
            )

        redis = Redis.from_url(self.settings.redis_url)
        try:
            queue_depth = int(await redis.zcard("arq:queue"))
            worker_available = bool(await redis.exists("conversation-os:worker:health"))
        except Exception:
            queue_depth = None
            worker_available = False
        finally:
            await redis.aclose()
        return InfrastructureMetrics(
            processing_mode="queue",
            queue_depth=queue_depth,
            worker_available=worker_available,
        )

    def _build_alerts(
        self,
        failed: int,
        retry_exhausted: int,
        infrastructure: InfrastructureMetrics,
    ) -> list[OperationalAlert]:
        alerts: list[OperationalAlert] = []
        if infrastructure.processing_mode == "queue" and not infrastructure.worker_available:
            alerts.append(
                OperationalAlert(
                    severity="critical",
                    code="worker_unavailable",
                    message="The processing worker heartbeat is unavailable.",
                )
            )
        if (
            infrastructure.queue_depth is not None
            and infrastructure.queue_depth >= self.settings.operations_queue_alert_threshold
        ):
            alerts.append(
                OperationalAlert(
                    severity="high",
                    code="queue_backlog",
                    message=(
                        f"The processing queue contains {infrastructure.queue_depth} jobs, "
                        f"meeting the alert threshold of "
                        f"{self.settings.operations_queue_alert_threshold}."
                    ),
                )
            )
        if retry_exhausted:
            alerts.append(
                OperationalAlert(
                    severity="high",
                    code="retry_exhausted",
                    message=f"{retry_exhausted} conversations exhausted all processing retries.",
                )
            )
        elif failed:
            alerts.append(
                OperationalAlert(
                    severity="warning",
                    code="processing_failures",
                    message=f"{failed} conversations failed processing and need review.",
                )
            )
        return alerts
