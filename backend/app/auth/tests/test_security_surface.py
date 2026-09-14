"""HTTP → real services → PostgreSQL isolation; only external edges are faked.

Clerk verification is replaced with two deterministic verified token results.
The actual authentication dependency and all repository predicates remain active.
Never run repository tests against a deployment database (fixtures truncate data).
"""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.client.models import Client, ClientFact
from app.client.repository import ClientRepository
from app.client.service import ClientNotFoundError, ClientService
from app.conversation.api import get_storage_backend
from app.conversation.enums import ConversationSource, ConversationStatus
from app.conversation.models import Conversation
from app.conversation.repository import ConversationRepository
from app.conversation.service import ConversationNotFoundError, ConversationService
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.dashboard.models import ClientFollowupAction, FollowupAction
from app.dashboard.repository import DashboardRepository
from app.main import app
from app.memory.models import ActionItem, ActionStatus, Decision, Memory, Person
from app.memory.repository import MemoryRepository
from app.transcription.enums import TranscriptionStatus
from app.transcription.models import Transcript
from app.transcription.repository import TranscriptRepository


@pytest_asyncio.fixture
async def security(db_session, monkeypatch):
    records = {}
    for owner in ("alpha", "beta"):
        marker = f"private_{owner}"
        client = Client(
            owner_id=owner, full_name=marker, role="buyer", email=f"{marker}@test.invalid"
        )
        db_session.add(client)
        await db_session.flush()
        conversation = Conversation(
            owner_id=owner,
            title=marker,
            filename=f"{marker}.wav",
            storage_path=f"s3://private/conversations/{marker}.wav",
            mime_type="audio/wav",
            file_size=10,
            status=ConversationStatus.COMPLETED,
            source=ConversationSource.UPLOAD,
            client_id=client.id,
            processing_attempts=1,
        )
        db_session.add(conversation)
        await db_session.flush()
        memory = Memory(
            conversation_id=conversation.id,
            summary=marker,
            topics=[marker],
            confidence=0.9,
            source="test",
            people=[Person(name=marker, client_id=client.id)],
            decisions=[Decision(description=marker)],
            action_items=[ActionItem(task=marker)],
        )
        transcript = Transcript(
            conversation_id=conversation.id,
            text=marker,
            status=TranscriptionStatus.COMPLETED,
        )
        db_session.add_all([memory, transcript])
        await db_session.flush()
        fact = ClientFact(
            client_id=client.id,
            fact_text=marker,
            source_conversation_id=conversation.id,
            source_memory_id=memory.id,
        )
        db_session.add_all(
            [
                fact,
                ClientFollowupAction(
                    client_id=client.id,
                    action=FollowupAction.RECORD_CONTACT,
                ),
            ]
        )
        failed = Conversation(
            owner_id=owner,
            title=f"{marker}_failed",
            filename=f"{marker}_failed.wav",
            storage_path=f"s3://private/conversations/{marker}_failed.wav",
            mime_type="audio/wav",
            file_size=10,
            status=ConversationStatus.FAILED,
            source=ConversationSource.UPLOAD,
            processing_attempts=3,
            processing_error="Processing failed.",
        )
        db_session.add(failed)
        await db_session.commit()
        records[owner] = SimpleNamespace(
            owner=owner,
            marker=marker,
            client=client.id,
            conversation=conversation.id,
            memory=memory.id,
            transcript=transcript.id,
            action=memory.action_items[0].id,
            person=memory.people[0].id,
            failed=failed.id,
            fact=fact.id,
        )
    # Request sessions are independent of seed objects and each other.
    maker = async_sessionmaker(db_session.bind, expire_on_commit=False)

    async def session_dependency():
        async with maker() as session:
            yield session

    settings = Settings(
        auth_enabled=True,
        clerk_secret_key="sk_test_example",
        processing_mode="queue",
        anthropic_api_key=None,
    )

    def verify(_self, request, _options):
        token = request.headers.get("authorization", "")
        owner = token.removeprefix("Bearer ")
        return SimpleNamespace(
            is_authenticated=owner in records,
            payload=(
                {"sub": owner, "org_id": "same_org", "org_role": "org:admin"}
                if owner in records
                else None
            ),
        )

    monkeypatch.setattr("app.auth.dependencies.Clerk.authenticate_request", verify)
    storage = SimpleNamespace(
        save=AsyncMock(return_value="s3://private/conversations/new.wav"),
        read=AsyncMock(return_value=b"audio"),
        delete=AsyncMock(),
    )
    enqueue = AsyncMock()
    monkeypatch.setattr("app.conversation.api.enqueue_conversation_processing", enqueue)
    monkeypatch.setattr("app.conversation.api.enqueue_conversation_retry", enqueue)
    saved_overrides = app.dependency_overrides.copy()
    app.dependency_overrides.update(
        {
            get_db_session: session_dependency,
            get_settings: lambda: settings,
            get_storage_backend: lambda: storage,
        }
    )
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as http:
        yield SimpleNamespace(
            records=records,
            http=http,
            storage=storage,
            enqueue=enqueue,
            maker=maker,
            settings=settings,
        )
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved_overrides)


def headers(actor):
    return {"Authorization": f"Bearer {actor}", "X-User-Id": "forged", "X-Role": "admin"}


def targeted(record):
    return [
        ("GET", f"/conversations/{record.conversation}", None),
        ("DELETE", f"/conversations/{record.conversation}", None),
        ("POST", f"/conversations/{record.failed}/retry", None),
        ("POST", f"/conversations/{record.conversation}/retry", None),
        ("GET", f"/clients/{record.client}", None),
        ("GET", f"/clients/{record.client}/conversations", None),
        ("GET", f"/transcriptions/by-conversation/{record.conversation}", None),
        ("GET", f"/memories/by-conversation/{record.conversation}", None),
        ("GET", f"/memories/{record.memory}", None),
        ("POST", f"/memories/action-items/{record.action}/complete", None),
        ("POST", f"/memories/action-items/{record.action}/reopen", None),
        ("POST", f"/dashboard/recommendations/{record.client}/actions", {"action": "complete"}),
    ]


@pytest.mark.parametrize("actor", ["alpha", "beta"])
async def test_foreign_ids_match_missing_ids_without_side_effects(security, actor):
    foreign = security.records["beta" if actor == "alpha" else "alpha"]
    for method, path, body in targeted(foreign):
        missing = path
        for value in vars(foreign).values():
            if isinstance(value, uuid.UUID):
                missing = missing.replace(str(value), str(uuid.UUID(int=0)))
        denied = await security.http.request(
            method, f"/api/v1{path}", json=body, headers=headers(actor)
        )
        absent = await security.http.request(
            method, f"/api/v1{missing}", json=body, headers=headers(actor)
        )
        assert denied.status_code == absent.status_code == 404, (path, denied.text, absent.text)
        normalized = denied.text
        for value in vars(foreign).values():
            if isinstance(value, uuid.UUID):
                normalized = normalized.replace(str(value), str(uuid.UUID(int=0)))
        assert normalized == absent.text
        assert foreign.marker not in denied.text
    security.storage.delete.assert_not_awaited()
    security.storage.read.assert_not_awaited()
    security.enqueue.assert_not_awaited()
    async with security.maker() as session:
        assert await session.get(Conversation, foreign.conversation) is not None
        assert (await session.get(Conversation, foreign.failed)).status == ConversationStatus.FAILED
        assert (await session.get(ActionItem, foreign.action)).status == ActionStatus.OPEN


@pytest.mark.parametrize("actor", ["alpha", "beta"])
@pytest.mark.parametrize("method", ["POST", "DELETE"])
async def test_nested_link_substitution(security, actor, method):
    own = security.records[actor]
    foreign = security.records["beta" if actor == "alpha" else "alpha"]
    for client_id, conversation_id in [
        (own.client, foreign.conversation),
        (foreign.client, own.conversation),
        (foreign.client, foreign.conversation),
        (uuid.uuid4(), own.conversation),
        (own.client, uuid.uuid4()),
    ]:
        response = await security.http.request(
            method,
            f"/api/v1/clients/{client_id}/conversations/{conversation_id}",
            headers=headers(actor),
        )
        assert response.status_code == 404, response.text
    async with security.maker() as session:
        for record in (own, foreign):
            assert (await session.get(Conversation, record.conversation)).client_id == record.client


@pytest.mark.parametrize("actor", ["alpha", "beta"])
async def test_lists_search_dashboard_results_and_operations(security, actor, monkeypatch):
    own = security.records[actor]
    foreign = security.records["beta" if actor == "alpha" else "alpha"]
    # No shared infrastructure access, even if a verified organization role is admin.
    redis_access = Mock(side_effect=AssertionError("Tenant endpoint accessed shared Redis"))
    monkeypatch.setattr("redis.asyncio.Redis.from_url", redis_access)
    paths = [
        ("GET", "/conversations"),
        ("GET", "/clients"),
        ("GET", "/memories"),
        ("GET", "/dashboard"),
        ("POST", "/dashboard/briefing"),
        ("GET", "/operations"),
        ("GET", f"/clients/{own.client}"),
        ("GET", f"/clients/{own.client}/conversations"),
        ("GET", f"/transcriptions/by-conversation/{own.conversation}"),
        ("GET", f"/memories/by-conversation/{own.conversation}"),
        ("GET", f"/memories/{own.memory}"),
        ("GET", f"/conversations/{own.conversation}"),
    ]
    for method, path in paths:
        response = await security.http.request(method, f"/api/v1{path}", headers=headers(actor))
        assert response.status_code == 200, (path, response.text)
        assert foreign.marker not in response.text
        assert "s3://" not in response.text and "storage_path" not in response.text
        for key in ("client", "conversation", "memory", "transcript", "person", "action", "failed"):
            assert str(getattr(foreign, key)) not in response.text
        if path == "/operations":
            data = response.json()["data"]
            assert data["processing"]["total"] == 2
            assert data["processing"]["failed"] == 1
            assert data["processing"]["completed"] == 1
            assert data["infrastructure"]["queue_depth"] is None
            assert data["infrastructure"]["worker_available"] is None
            assert [a["code"] for a in data["alerts"]] == ["retry_exhausted"]
    redis_access.assert_not_called()
    for path in [
        f"/conversations?search={foreign.marker}&status=COMPLETED&limit=1",
        f"/clients?search={foreign.marker}&role=buyer&limit=1",
        f"/clients?search={foreign.marker}@test.invalid",
        "/conversations?offset=2",
        "/clients?offset=1",
    ]:
        response = await security.http.get(f"/api/v1{path}", headers=headers(actor))
        assert response.status_code == 200 and response.json()["data"] == []
    for path in ("/clients?search=%25", "/conversations?search=%25"):
        response = await security.http.get(f"/api/v1{path}", headers=headers(actor))
        assert response.status_code == 200 and foreign.marker not in response.text


@pytest.mark.parametrize("actor", ["alpha", "beta"])
async def test_owner_success_and_upload_ignores_forged_owner(security, actor):
    own = security.records[actor]
    foreign = security.records["beta" if actor == "alpha" else "alpha"]
    response = await security.http.post(
        f"/api/v1/conversations?owner_id={foreign.owner}&storage_path=s3://foreign/key",
        headers=headers(actor),
        files={"file": ("new.wav", b"audio", "audio/wav")},
    )
    assert response.status_code == 200, response.text
    uploaded = uuid.UUID(response.json()["data"]["id"])
    async with security.maker() as session:
        record = await session.get(Conversation, uploaded)
        assert record.owner_id == actor
        assert record.storage_path == "s3://private/conversations/new.wav"
    assert security.enqueue.await_args.args[1] == actor
    for method in ("DELETE", "POST"):
        response = await security.http.request(
            method,
            f"/api/v1/clients/{own.client}/conversations/{own.conversation}",
            headers=headers(actor),
        )
        assert response.status_code == 204
    for operation in ("complete", "reopen"):
        response = await security.http.post(
            f"/api/v1/memories/action-items/{own.action}/{operation}",
            headers=headers(actor),
        )
        assert response.status_code == 200
    for action in ("complete", "record_contact", "snooze"):
        body = {"action": action}
        if action == "snooze":
            body["snooze_days"] = 3
        response = await security.http.post(
            f"/api/v1/dashboard/recommendations/{own.client}/actions",
            headers=headers(actor),
            json=body,
        )
        assert response.status_code == 200, response.text
    response = await security.http.post(
        f"/api/v1/conversations/{own.failed}/retry", headers=headers(actor)
    )
    assert response.status_code == 200
    assert security.enqueue.await_args.args[1] == actor
    response = await security.http.delete(
        f"/api/v1/conversations/{uploaded}", headers=headers(actor)
    )
    assert response.status_code == 204
    security.storage.delete.assert_awaited_once_with("s3://private/conversations/new.wav")


async def test_every_business_route_requires_authentication(security):
    # OpenAPI enumeration prevents a new operation silently escaping this check.
    schema = app.openapi()
    count = 0
    for path, methods in schema["paths"].items():
        if not path.startswith("/api/v1/"):
            continue
        for method, operation in methods.items():
            concrete = path
            for parameter in operation.get("parameters", []):
                if parameter["in"] == "path":
                    concrete = concrete.replace("{" + parameter["name"] + "}", str(uuid.uuid4()))
            for token in (None, "invalid", "forged-admin"):
                kwargs = {"headers": headers(token)} if token else {}
                if concrete == "/api/v1/conversations" and method == "post":
                    kwargs["files"] = {"file": ("test.wav", b"audio", "audio/wav")}
                elif concrete.endswith("/actions"):
                    kwargs["json"] = {"action": "complete"}
                response = await security.http.request(method, concrete, **kwargs)
                assert response.status_code == 401, (method, concrete, response.text)
            count += 1
    assert count == 21
    security.storage.save.assert_not_awaited()
    security.enqueue.assert_not_awaited()


@pytest.mark.parametrize("actor", ["alpha", "beta"])
async def test_internal_link_and_provenance_guards(security, actor):
    own = security.records[actor]
    foreign = security.records["beta" if actor == "alpha" else "alpha"]
    async with security.maker() as session:
        memories = MemoryRepository(session, actor)
        assert await TranscriptRepository(session, actor).get(foreign.transcript) is None
        assert (await TranscriptRepository(session, actor).get(own.transcript)).id == own.transcript
        for person, client in [(foreign.person, own.client), (own.person, foreign.client)]:
            with pytest.raises(ValueError, match="not found"):
                await memories.set_person_client(person, client)
        service = ConversationService(
            ConversationRepository(session, actor),
            security.storage,
            allowed_mime_types=("audio/wav",),
            max_upload_size_bytes=100,
        )
        with pytest.raises(ConversationNotFoundError):
            await service.update_client(own.conversation, foreign.client)
        clients = ClientService(ClientRepository(session, actor))
        for client, conv, memory in [
            (foreign.client, own.conversation, own.memory),
            (own.client, foreign.conversation, foreign.memory),
            (own.client, own.conversation, foreign.memory),
        ]:
            with pytest.raises(ClientNotFoundError):
                await clients.record_facts(
                    client_id=client,
                    fact_texts=["must not persist"],
                    source_conversation_id=conv,
                    source_memory_id=memory,
                    confidence=0.9,
                )
        await memories.set_person_client(own.person, own.client)
        await service.update_client(own.conversation, own.client)
        await clients.record_facts(
            client_id=own.client,
            fact_texts=["valid"],
            source_conversation_id=own.conversation,
            source_memory_id=own.memory,
            confidence=0.9,
        )


@pytest.mark.parametrize("actor", ["alpha", "beta"])
async def test_inconsistent_foreign_relations_do_not_leak(security, actor):
    own = security.records[actor]
    foreign = security.records["beta" if actor == "alpha" else "alpha"]
    async with security.maker() as session:
        (await session.get(Conversation, foreign.conversation)).client_id = own.client
        (await session.get(Person, foreign.person)).client_id = own.client
        (await session.get(ClientFact, foreign.fact)).client_id = own.client
        await session.commit()
    for path in (f"/clients/{own.client}", "/dashboard"):
        response = await security.http.get(f"/api/v1{path}", headers=headers(actor))
        assert response.status_code == 200
        assert foreign.marker not in response.text
        assert str(foreign.conversation) not in response.text
    # Reverse direction: owned action → foreign client must not expose its name.
    async with security.maker() as session:
        (await session.get(Conversation, own.conversation)).client_id = foreign.client
        await session.commit()
        repository = DashboardRepository(session, actor)
        assert all(row.client_name is None for row in await repository.list_open_action_items())
        action = await session.get(ActionItem, own.action)
        action.status = ActionStatus.COMPLETED
        action.completed_at = datetime.now(UTC)
        await session.commit()
        assert all(
            row.client_name is None for row in await repository.list_recent_completed_actions()
        )


@pytest.mark.parametrize("actor", ["alpha", "beta"])
@pytest.mark.parametrize("retry_attempts", [None, 3])
async def test_worker_wrong_owner_cannot_read_storage_or_mutate(
    security, actor, retry_attempts, monkeypatch
):
    from app.orchestrator.dependencies import build_conversation_processing_orchestrator
    from app.processing import worker

    foreign = security.records["beta" if actor == "alpha" else "alpha"]
    provider = SimpleNamespace(transcribe=AsyncMock(), complete=AsyncMock())
    monkeypatch.setattr(worker, "AsyncSessionLocal", security.maker)
    monkeypatch.setattr(worker, "get_settings", lambda: security.settings)
    monkeypatch.setattr(worker, "build_storage_backend", lambda _settings: security.storage)
    monkeypatch.setattr("app.orchestrator.dependencies.get_ai_provider", lambda _settings: provider)
    monkeypatch.setattr(
        "app.orchestrator.dependencies.get_transcription_provider", lambda _settings: provider
    )
    monkeypatch.setattr(
        worker,
        "build_conversation_processing_orchestrator",
        build_conversation_processing_orchestrator,
    )
    if retry_attempts is None:
        with pytest.raises(RuntimeError):
            await worker.process_conversation({"job_try": 3}, str(foreign.failed), actor)
    else:
        await worker.process_conversation(
            {"job_try": 1}, str(foreign.failed), actor, retry_attempts
        )
    security.storage.read.assert_not_awaited()
    security.storage.delete.assert_not_awaited()
    provider.transcribe.assert_not_awaited()
    provider.complete.assert_not_awaited()
    async with security.maker() as session:
        failed = await session.get(Conversation, foreign.failed)
        assert failed.status == ConversationStatus.FAILED and failed.processing_attempts == 3
        assert (
            await session.scalar(
                select(Transcript.id).where(Transcript.conversation_id == foreign.failed)
            )
            is None
        )


async def test_no_object_or_raw_job_http_access(security):
    record = security.records["beta"]
    for path in [
        f"/api/v1/conversations/{record.conversation}/download",
        f"/api/v1/conversations/{record.conversation}/status",
        f"/api/v1/jobs/{record.conversation}",
        f"/storage/conversations/{record.marker}.wav",
        f"/conversations/{record.marker}.wav",
    ]:
        response = await security.http.get(path, headers=headers("alpha"))
        assert response.status_code == 404
    security.storage.read.assert_not_awaited()


@pytest.mark.parametrize("actor", ["alpha", "beta"])
async def test_foreign_activity_cannot_change_operations(security, actor):
    foreign = security.records["beta" if actor == "alpha" else "alpha"]
    before = await security.http.get("/api/v1/operations", headers=headers(actor))
    async with security.maker() as session:
        row = await session.get(Conversation, foreign.failed)
        row.status = ConversationStatus.QUEUED
        row.processing_attempts = 99
        await session.commit()
    after = await security.http.get("/api/v1/operations", headers=headers(actor))
    assert before.status_code == after.status_code == 200
    before_data, after_data = before.json()["data"], after.json()["data"]
    before_data.pop("observed_at")
    after_data.pop("observed_at")
    assert before_data == after_data


@pytest.mark.parametrize("actor", ["alpha", "beta"])
async def test_briefing_provider_receives_only_actor_data(security, actor, monkeypatch):
    own = security.records[actor]
    foreign = security.records["beta" if actor == "alpha" else "alpha"]
    provider = SimpleNamespace(
        complete=AsyncMock(return_value=SimpleNamespace(content="Test briefing.", model="test"))
    )
    security.settings.anthropic_api_key = "test-placeholder"
    monkeypatch.setattr("app.dashboard.api.get_ai_provider", lambda _settings: provider)
    response = await security.http.post("/api/v1/dashboard/briefing", headers=headers(actor))
    assert response.status_code == 200
    prompt = provider.complete.await_args.args[0][0].content
    assert own.marker in prompt
    assert foreign.marker not in prompt
    assert str(foreign.client) not in prompt
