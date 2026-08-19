from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.dashboard.models import FollowupAction
from app.dashboard.schemas import DashboardOverview, FollowupActionRequest
from app.dashboard.service import DashboardService


def _service(now: datetime) -> DashboardService:
    return DashboardService(
        conversation_service=SimpleNamespace(),
        client_service=SimpleNamespace(),
        clock=lambda: now,
    )


def test_builds_failed_processing_alert() -> None:
    service = _service(datetime(2026, 8, 17, tzinfo=UTC))

    assert service._build_alerts(2) == ["2 conversations failed processing and need review."]
    assert service._build_alerts(1) == ["1 conversation failed processing and needs review."]
    assert service._build_alerts(0) == []


def test_builds_followup_for_stale_client() -> None:
    now = datetime(2026, 8, 17, tzinfo=UTC)
    client = SimpleNamespace(
        id=uuid4(),
        full_name="John",
        conversations=[SimpleNamespace(created_at=datetime(2026, 8, 9, tzinfo=UTC))],
    )

    assert _service(now)._build_followups([client]) == [
        "Follow up with John; last conversation was 8 days ago."
    ]


def test_builds_followup_for_client_without_conversations() -> None:
    now = datetime(2026, 8, 17, tzinfo=UTC)
    client = SimpleNamespace(id=uuid4(), full_name="Sarah", conversations=[])

    assert _service(now)._build_followups([client]) == ["Schedule a first conversation with Sarah."]


def test_does_not_build_followup_for_recent_contact() -> None:
    now = datetime(2026, 8, 17, tzinfo=UTC)
    client = SimpleNamespace(
        id=uuid4(),
        full_name="Mike",
        conversations=[SimpleNamespace(created_at=datetime(2026, 8, 15, tzinfo=UTC))],
    )

    assert _service(now)._build_followups([client]) == []


def test_priorities_rank_failures_before_stale_followups() -> None:
    now = datetime(2026, 8, 17, tzinfo=UTC)
    client_id = uuid4()
    client = SimpleNamespace(
        id=client_id,
        full_name="John",
        conversations=[SimpleNamespace(created_at=datetime(2026, 8, 9, tzinfo=UTC))],
    )

    priorities = _service(now)._build_priorities(3, [client])

    assert [priority.rank for priority in priorities] == [1, 2]
    assert priorities[0].category == "processing"
    assert priorities[0].severity == "critical"
    assert priorities[1].title == "Follow up with John"
    assert priorities[1].href == f"/clients/{client_id}"


def test_priorities_rank_oldest_followup_first() -> None:
    now = datetime(2026, 8, 17, tzinfo=UTC)
    clients = [
        SimpleNamespace(
            id=uuid4(),
            full_name="Recent",
            conversations=[SimpleNamespace(created_at=datetime(2026, 8, 9, tzinfo=UTC))],
        ),
        SimpleNamespace(
            id=uuid4(),
            full_name="Oldest",
            conversations=[SimpleNamespace(created_at=datetime(2026, 8, 1, tzinfo=UTC))],
        ),
    ]

    priorities = _service(now)._build_priorities(0, clients)

    assert priorities[0].title == "Follow up with Oldest"
    assert priorities[1].title == "Follow up with Recent"


def test_client_recommendations_rank_oldest_contact_first() -> None:
    now = datetime(2026, 8, 17, tzinfo=UTC)
    oldest_id = uuid4()
    clients = [
        SimpleNamespace(
            id=uuid4(),
            full_name="Recent",
            conversations=[SimpleNamespace(created_at=datetime(2026, 8, 9, tzinfo=UTC))],
        ),
        SimpleNamespace(
            id=oldest_id,
            full_name="Oldest",
            conversations=[
                SimpleNamespace(created_at=datetime(2026, 7, 28, tzinfo=UTC)),
                SimpleNamespace(created_at=datetime(2026, 8, 1, tzinfo=UTC)),
            ],
        ),
    ]

    recommendations = _service(now)._build_client_recommendations(clients)

    assert [item.rank for item in recommendations] == [1, 2]
    assert recommendations[0].client_id == oldest_id
    assert recommendations[0].days_since_contact == 16
    assert recommendations[0].conversation_count == 2
    assert recommendations[0].urgency_score == 66
    assert recommendations[0].recommended_action == "Follow up today."


def test_client_recommendations_include_first_conversation() -> None:
    now = datetime(2026, 8, 17, tzinfo=UTC)
    client = SimpleNamespace(
        id=uuid4(),
        full_name="New Client",
        conversations=[],
    )

    recommendations = _service(now)._build_client_recommendations([client])

    assert len(recommendations) == 1
    assert recommendations[0].days_since_contact is None
    assert recommendations[0].urgency_score == 50
    assert recommendations[0].recommended_action == ("Schedule a first conversation.")


def test_client_recommendations_exclude_recent_contact() -> None:
    now = datetime(2026, 8, 17, tzinfo=UTC)
    client = SimpleNamespace(
        id=uuid4(),
        full_name="Current Client",
        conversations=[SimpleNamespace(created_at=datetime(2026, 8, 15, tzinfo=UTC))],
    )

    assert _service(now)._build_client_recommendations([client]) == []


def test_open_actions_make_recent_client_actionable() -> None:
    now = datetime(2026, 8, 17, tzinfo=UTC)
    client = SimpleNamespace(
        id=uuid4(),
        full_name="Active Buyer",
        conversations=[SimpleNamespace(created_at=datetime(2026, 8, 16, tzinfo=UTC))],
    )

    recommendations = _service(now)._build_client_recommendations(
        [client], open_action_counts={client.id: 2}
    )

    assert len(recommendations) == 1
    assert recommendations[0].urgency_score == 80
    assert recommendations[0].open_action_count == 2
    assert recommendations[0].recommended_action == ("Complete the next open action.")


def test_snoozed_recommendation_is_temporarily_excluded() -> None:
    now = datetime(2026, 8, 17, tzinfo=UTC)
    client = SimpleNamespace(
        id=uuid4(),
        full_name="Snoozed Client",
        conversations=[],
    )
    action = SimpleNamespace(
        action=FollowupAction.SNOOZE,
        snoozed_until=datetime(2026, 8, 18, tzinfo=UTC),
        created_at=now,
    )

    recommendations = _service(now)._build_client_recommendations([client], {client.id: action})

    assert recommendations == []
    assert _service(now)._build_followups([client], {client.id: action}) == []
    assert _service(now)._build_priorities(0, [client], {client.id: action}) == []
    assert _service(now)._count_due_followups([client], {client.id: action}) == 0


def test_recorded_contact_resets_followup_clock() -> None:
    now = datetime(2026, 8, 17, tzinfo=UTC)
    client = SimpleNamespace(
        id=uuid4(),
        full_name="Contacted Client",
        conversations=[SimpleNamespace(created_at=datetime(2026, 8, 1, tzinfo=UTC))],
    )
    action = SimpleNamespace(
        action=FollowupAction.RECORD_CONTACT,
        snoozed_until=None,
        created_at=datetime(2026, 8, 16, tzinfo=UTC),
    )

    recommendations = _service(now)._build_client_recommendations([client], {client.id: action})

    assert recommendations == []


def test_completed_recommendation_returns_after_new_activity() -> None:
    now = datetime(2026, 8, 17, tzinfo=UTC)
    client = SimpleNamespace(
        id=uuid4(),
        full_name="Returning Client",
        conversations=[SimpleNamespace(created_at=datetime(2026, 8, 2, tzinfo=UTC))],
    )
    action = SimpleNamespace(
        action=FollowupAction.COMPLETE,
        snoozed_until=None,
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
    )

    recommendations = _service(now)._build_client_recommendations([client], {client.id: action})

    assert len(recommendations) == 1
    assert recommendations[0].days_since_contact == 15


async def test_records_snooze_action_with_expiration() -> None:
    now = datetime(2026, 8, 17, tzinfo=UTC)
    client_id = uuid4()

    class Clients:
        async def get_profile(self, requested_id):
            assert requested_id == client_id
            return SimpleNamespace(id=requested_id)

    class Repository:
        saved = None

        async def add_followup_action(self, action):
            self.saved = action
            return action

    repository = Repository()
    service = DashboardService(
        conversation_service=SimpleNamespace(),
        client_service=Clients(),
        repository=repository,
        clock=lambda: now,
    )

    result = await service.record_followup_action(
        client_id,
        FollowupActionRequest(action="snooze", snooze_days=3),
    )

    assert repository.saved.action == FollowupAction.SNOOZE
    assert repository.saved.snoozed_until == datetime(2026, 8, 20, tzinfo=UTC)
    assert result.action == "snooze"
    assert result.recorded_at == now


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


def test_builds_explainable_recent_activity() -> None:
    now = datetime(2026, 8, 17, tzinfo=UTC)
    client_id = uuid4()
    action_id = uuid4()
    records = [
        SimpleNamespace(
            client_name="John",
            action=SimpleNamespace(
                id=action_id,
                client_id=client_id,
                action=FollowupAction.SNOOZE,
                created_at=now,
                snoozed_until=datetime(2026, 8, 18, tzinfo=UTC),
            ),
        )
    ]

    activity = DashboardService._build_recent_activity(records)

    assert len(activity) == 1
    assert activity[0].id == action_id
    assert activity[0].action == "snooze"
    assert activity[0].description == ("Snoozed the follow-up recommendation for John.")
    assert activity[0].href == f"/clients/{client_id}"


def test_merges_completed_action_items_into_recent_activity() -> None:
    now = datetime(2026, 8, 17, tzinfo=UTC)
    action_id = uuid4()
    conversation_id = uuid4()
    completed = [
        SimpleNamespace(
            action_item=SimpleNamespace(
                id=action_id,
                task="Send the property list",
                completed_at=now,
            ),
            client_id=None,
            client_name=None,
            conversation_id=conversation_id,
        )
    ]

    activity = DashboardService._build_recent_activity([], completed)

    assert len(activity) == 1
    assert activity[0].action == "complete_action_item"
    assert activity[0].description == ('Completed action item "Send the property list".')
    assert activity[0].href == f"/conversations/{conversation_id}"
