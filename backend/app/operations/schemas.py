from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ProcessingMetrics(BaseModel):
    total: int
    queued: int
    processing: int
    completed: int
    failed: int
    retry_exhausted: int
    average_duration_seconds: float | None


class InfrastructureMetrics(BaseModel):
    processing_mode: Literal["inline", "queue"]
    queue_depth: int | None
    worker_available: bool | None


class OperationalAlert(BaseModel):
    severity: Literal["critical", "high", "warning"]
    code: str
    message: str


class OperationalStatus(BaseModel):
    processing: ProcessingMetrics
    infrastructure: InfrastructureMetrics
    alerts: list[OperationalAlert]
    observed_at: datetime
