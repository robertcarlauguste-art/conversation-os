from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response.headers


async def test_version() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/version")
    assert response.status_code == 200
    body = response.json()
    assert "app_name" in body
    assert "version" in body


async def test_unknown_route_returns_404_with_request_id() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/does-not-exist")
    assert response.status_code == 404
    assert "X-Request-ID" in response.headers
