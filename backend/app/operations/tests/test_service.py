from datetime import UTC, datetime

from app.core.config import Settings
from app.operations.schemas import InfrastructureMetrics, ProcessingMetrics
from app.operations.service import OperationsService


class FakeRepository:
    def __init__(self, metrics: ProcessingMetrics) -> None:
        self.metrics = metrics
        self.received_max_tries: int | None = None

    async def processing_metrics(self, max_tries: int) -> ProcessingMetrics:
        self.received_max_tries = max_tries
        return self.metrics


def _metrics(*, failed: int = 0, retry_exhausted: int = 0) -> ProcessingMetrics:
    return ProcessingMetrics(
        total=10,
        queued=0,
        processing=0,
        completed=10 - failed,
        failed=failed,
        retry_exhausted=retry_exhausted,
        average_duration_seconds=12.5,
    )


async def test_inline_status_marks_queue_metrics_not_applicable() -> None:
    repository = FakeRepository(_metrics())
    now = datetime(2026, 8, 21, tzinfo=UTC)
    service = OperationsService(repository, Settings(), clock=lambda: now)  # type: ignore[arg-type]

    result = await service.get_status()

    assert result.observed_at == now
    assert result.infrastructure.processing_mode == "inline"
    assert result.infrastructure.queue_depth is None
    assert result.infrastructure.worker_available is None
    assert result.alerts == []
    assert repository.received_max_tries == 3


def test_alerts_prioritize_worker_backlog_and_exhausted_retries() -> None:
    settings = Settings(
        processing_mode="queue",
        operations_queue_alert_threshold=5,
    )
    service = OperationsService(FakeRepository(_metrics()), settings)  # type: ignore[arg-type]
    infrastructure = InfrastructureMetrics(
        processing_mode="queue",
        queue_depth=7,
        worker_available=False,
    )

    alerts = service._build_alerts(3, 2, infrastructure)

    assert [alert.code for alert in alerts] == [
        "worker_unavailable",
        "queue_backlog",
        "retry_exhausted",
    ]
    assert [alert.severity for alert in alerts] == ["critical", "high", "high"]


def test_non_exhausted_failure_is_warning() -> None:
    service = OperationsService(FakeRepository(_metrics()), Settings())  # type: ignore[arg-type]
    infrastructure = InfrastructureMetrics(
        processing_mode="inline",
        queue_depth=None,
        worker_available=None,
    )

    alerts = service._build_alerts(1, 0, infrastructure)

    assert len(alerts) == 1
    assert alerts[0].code == "processing_failures"
    assert alerts[0].severity == "warning"
