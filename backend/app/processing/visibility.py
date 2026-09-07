"""Safe diagnostics; stale means overdue, not proof of abandonment."""

from datetime import UTC, datetime

from app.core.config import get_settings

SAFE_ERRORS = {
    "Upload failed. Check storage and database availability.",
    "Processing could not start. Check provider configuration.",
    "Processing result could not be saved. Check database availability.",
    "Memory extraction failed. Check the extraction provider configuration.",
    "Client reconciliation failed. Check database availability.",
    "Processing failed. Check provider configuration and worker availability.",
    "Transcription failed. Check recording format and transcription provider configuration.",
    "Processing could not be queued. Check queue and worker availability.",
}


def safe_error(value: str | None) -> str | None:
    # Never echo arbitrary provider bodies, even after regex redaction.
    if not value:
        return None
    return (
        value
        if value in SAFE_ERRORS
        else "Processing failed. Check provider configuration and worker availability."
    )


def stale_threshold_seconds() -> int:
    return max(900, get_settings().processing_job_timeout_seconds + 60)


def is_stale(
    status: str, created_at: datetime, started_at: datetime | None, now: datetime | None = None
) -> bool:
    if status not in ("QUEUED", "PROCESSING"):
        return False
    since = started_at if status == "PROCESSING" and started_at else created_at
    observed = now or datetime.now(UTC)
    # Legacy naive values and injected clocks are interpreted as UTC, never local time.
    since = since.replace(tzinfo=UTC) if since.tzinfo is None else since.astimezone(UTC)
    observed = observed.replace(tzinfo=UTC) if observed.tzinfo is None else observed.astimezone(UTC)
    return (observed - since).total_seconds() > stale_threshold_seconds()
