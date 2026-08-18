from datetime import datetime, timezone
from types import SimpleNamespace

from app.dashboard.service import DashboardService


def _service(now: datetime) -> DashboardService:
    return DashboardService(
        conversation_service=SimpleNamespace(),
        client_service=SimpleNamespace(),
        clock=lambda: now,
    )


def test_builds_failed_processing_alert() -> None:
    service = _service(datetime(2026, 8, 17, tzinfo=timezone.utc))

    assert service._build_alerts(2) == [
        "2 conversations failed processing and need review."
    ]
    assert service._build_alerts(1) == [
        "1 conversation failed processing and needs review."
    ]
    assert service._build_alerts(0) == []


def test_builds_followup_for_stale_client() -> None:
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    client = SimpleNamespace(
        full_name="John",
        conversations=[
            SimpleNamespace(
                created_at=datetime(2026, 8, 9, tzinfo=timezone.utc)
            )
        ],
    )

    assert _service(now)._build_followups([client]) == [
        "Follow up with John; last conversation was 8 days ago."
    ]


def test_builds_followup_for_client_without_conversations() -> None:
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    client = SimpleNamespace(full_name="Sarah", conversations=[])

    assert _service(now)._build_followups([client]) == [
        "Schedule a first conversation with Sarah."
    ]


def test_does_not_build_followup_for_recent_contact() -> None:
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    client = SimpleNamespace(
        full_name="Mike",
        conversations=[
            SimpleNamespace(
                created_at=datetime(2026, 8, 15, tzinfo=timezone.utc)
            )
        ],
    )

    assert _service(now)._build_followups([client]) == []
