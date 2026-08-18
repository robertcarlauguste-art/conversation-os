from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.dashboard.service import DashboardService
from app.dashboard.schemas import DashboardOverview


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
        id=uuid4(),
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
    client = SimpleNamespace(id=uuid4(), full_name="Sarah", conversations=[])

    assert _service(now)._build_followups([client]) == [
        "Schedule a first conversation with Sarah."
    ]


def test_does_not_build_followup_for_recent_contact() -> None:
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    client = SimpleNamespace(
        id=uuid4(),
        full_name="Mike",
        conversations=[
            SimpleNamespace(
                created_at=datetime(2026, 8, 15, tzinfo=timezone.utc)
            )
        ],
    )

    assert _service(now)._build_followups([client]) == []


def test_priorities_rank_failures_before_stale_followups() -> None:
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    client_id = uuid4()
    client = SimpleNamespace(
        id=client_id,
        full_name="John",
        conversations=[
            SimpleNamespace(
                created_at=datetime(2026, 8, 9, tzinfo=timezone.utc)
            )
        ],
    )

    priorities = _service(now)._build_priorities(3, [client])

    assert [priority.rank for priority in priorities] == [1, 2]
    assert priorities[0].category == "processing"
    assert priorities[0].severity == "critical"
    assert priorities[1].title == "Follow up with John"
    assert priorities[1].href == f"/clients/{client_id}"


def test_priorities_rank_oldest_followup_first() -> None:
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    clients = [
        SimpleNamespace(
            id=uuid4(),
            full_name="Recent",
            conversations=[
                SimpleNamespace(
                    created_at=datetime(2026, 8, 9, tzinfo=timezone.utc)
                )
            ],
        ),
        SimpleNamespace(
            id=uuid4(),
            full_name="Oldest",
            conversations=[
                SimpleNamespace(
                    created_at=datetime(2026, 8, 1, tzinfo=timezone.utc)
                )
            ],
        ),
    ]

    priorities = _service(now)._build_priorities(0, clients)

    assert priorities[0].title == "Follow up with Oldest"
    assert priorities[1].title == "Follow up with Recent"


def test_daily_brief_summarizes_dashboard_state() -> None:
    brief = DashboardService._build_daily_brief(
        DashboardOverview(
            clients=1,
            conversations=22,
            completed=9,
            processing=0,
            failed=13,
        ),
        due_followups=1,
    )

    assert [item.text for item in brief] == [
        "22 conversations stored.",
        "9 successfully processed.",
        "13 require attention.",
        "1 client tracked.",
        "1 follow-up due.",
    ]
    assert brief[2].tone == "warning"
    assert brief[4].tone == "warning"


def test_daily_brief_reports_healthy_empty_states() -> None:
    brief = DashboardService._build_daily_brief(
        DashboardOverview(
            clients=0,
            conversations=0,
            completed=0,
            processing=0,
            failed=0,
        ),
        due_followups=0,
    )

    assert brief[2].text == "No processing failures need attention."
    assert brief[2].tone == "positive"
    assert brief[4].text == "No follow-ups are due."
    assert brief[4].tone == "positive"
