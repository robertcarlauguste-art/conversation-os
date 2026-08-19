import io

import pytest
from httpx import ASGITransport, AsyncClient

from app.conversation.api import get_storage_backend
from app.conversation.storage import LocalStorageBackend
from app.main import app
from tests.fakes import FakeAIProvider, FakeTranscriptionProvider


async def _client(storage_backend: LocalStorageBackend) -> AsyncClient:
    app.dependency_overrides[get_storage_backend] = lambda: storage_backend
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _patch_providers_with_fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Patches where the names are *used* (app.orchestrator.dependencies),
    not where they're defined — standard mocking practice. This lets
    the real orchestrator, real services, and real DB all run for
    real; only the two external network calls are faked.
    """
    monkeypatch.setattr(
        "app.orchestrator.dependencies.get_ai_provider", lambda settings: FakeAIProvider()
    )
    monkeypatch.setattr(
        "app.orchestrator.dependencies.get_transcription_provider",
        lambda settings: FakeTranscriptionProvider(),
    )


async def test_upload_runs_full_pipeline_and_completes(
    storage_backend, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    With working providers (faked here), an upload should come back
    COMPLETED — transcribed, extracted, and persisted — by the time
    the HTTP response returns (Sprint 2 processes synchronously; see
    TD-003 in Sprint2.md).
    """
    _patch_providers_with_fakes(monkeypatch)

    async with await _client(storage_backend) as client:
        files = {"file": ("buyer_consultation.mp3", io.BytesIO(b"fake audio bytes"), "audio/mpeg")}
        upload_response = await client.post("/api/v1/conversations", files=files)
        assert upload_response.status_code == 200
        body = upload_response.json()
        assert body["success"] is True
        assert body["data"]["status"] == "COMPLETED"
        conversation_id = body["data"]["id"]

        memory_response = await client.get(f"/api/v1/memories/by-conversation/{conversation_id}")
        assert memory_response.status_code == 200
        assert memory_response.json()["data"]["conversation_id"] == conversation_id

        transcript_response = await client.get(
            f"/api/v1/transcriptions/by-conversation/{conversation_id}"
        )
        assert transcript_response.status_code == 200
        assert transcript_response.json()["data"]["status"] == "COMPLETED"

    app.dependency_overrides.clear()


async def test_upload_without_configured_ai_keys_still_succeeds_but_marks_failed(
    storage_backend,
) -> None:
    """
    No fakes patched in here — exercises the real
    get_ai_provider/get_transcription_provider path with no API keys
    configured (the default test environment). The upload itself must
    still succeed; only downstream processing should fail.
    """
    async with await _client(storage_backend) as client:
        files = {"file": ("buyer_consultation.mp3", io.BytesIO(b"fake audio bytes"), "audio/mpeg")}
        upload_response = await client.post("/api/v1/conversations", files=files)
        assert upload_response.status_code == 200
        body = upload_response.json()
        assert body["success"] is True
        assert body["data"]["status"] == "FAILED"

    app.dependency_overrides.clear()


async def test_upload_rejects_unsupported_file_type(storage_backend) -> None:
    async with await _client(storage_backend) as client:
        files = {"file": ("notes.txt", io.BytesIO(b"not audio"), "text/plain")}
        response = await client.post("/api/v1/conversations", files=files)
        assert response.status_code == 422
        assert "Unsupported file type" in response.json()["detail"]

    app.dependency_overrides.clear()


async def test_list_and_get_and_delete_round_trip(
    storage_backend, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_providers_with_fakes(monkeypatch)

    async with await _client(storage_backend) as client:
        files = {"file": ("buyer_consultation.mp3", io.BytesIO(b"fake audio bytes"), "audio/mpeg")}
        upload_response = await client.post("/api/v1/conversations", files=files)
        conversation_id = upload_response.json()["data"]["id"]

        list_response = await client.get("/api/v1/conversations")
        assert list_response.status_code == 200
        listed_ids = [item["id"] for item in list_response.json()["data"]]
        assert conversation_id in listed_ids

        detail_response = await client.get(f"/api/v1/conversations/{conversation_id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()["data"]
        assert detail["filename"] == "buyer_consultation.mp3"
        assert detail["file_size"] == len(b"fake audio bytes")

        delete_response = await client.delete(f"/api/v1/conversations/{conversation_id}")
        assert delete_response.status_code == 204

        missing_response = await client.get(f"/api/v1/conversations/{conversation_id}")
        assert missing_response.status_code == 404

    app.dependency_overrides.clear()


async def test_get_unknown_conversation_returns_404(storage_backend) -> None:
    async with await _client(storage_backend) as client:
        response = await client.get("/api/v1/conversations/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    app.dependency_overrides.clear()
