import io

from httpx import ASGITransport, AsyncClient

from app.conversation.api import get_storage_backend
from app.conversation.storage import LocalStorageBackend
from app.main import app


async def _client(storage_backend: LocalStorageBackend) -> AsyncClient:
    app.dependency_overrides[get_storage_backend] = lambda: storage_backend
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_upload_list_get_delete_round_trip(storage_backend) -> None:
    async with await _client(storage_backend) as client:
        files = {"file": ("buyer_consultation.mp3", io.BytesIO(b"fake audio bytes"), "audio/mpeg")}
        upload_response = await client.post("/api/v1/conversations", files=files)
        assert upload_response.status_code == 200
        body = upload_response.json()
        assert body["success"] is True
        assert body["data"]["status"] == "UPLOADED"
        conversation_id = body["data"]["id"]

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


async def test_upload_rejects_unsupported_file_type(storage_backend) -> None:
    async with await _client(storage_backend) as client:
        files = {"file": ("notes.txt", io.BytesIO(b"not audio"), "text/plain")}
        response = await client.post("/api/v1/conversations", files=files)
        assert response.status_code == 422
        assert "Unsupported file type" in response.json()["detail"]

    app.dependency_overrides.clear()


async def test_get_unknown_conversation_returns_404(storage_backend) -> None:
    async with await _client(storage_backend) as client:
        response = await client.get("/api/v1/conversations/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    app.dependency_overrides.clear()
