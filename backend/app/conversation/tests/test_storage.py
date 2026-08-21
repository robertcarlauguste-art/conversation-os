from io import BytesIO
from pathlib import Path

import pytest

from app.conversation.storage import (
    InvalidStorageLocationError,
    LocalStorageBackend,
    RoutingStorageBackend,
    S3StorageBackend,
)
from app.conversation.storage_factory import build_storage_backend
from app.core.config import Settings


@pytest.mark.asyncio
async def test_local_storage_uses_portable_location(tmp_path: Path) -> None:
    storage = LocalStorageBackend(root=str(tmp_path))

    location = await storage.save(filename="recording.wav", content=b"audio")

    assert location.startswith("local://conversations/")
    assert location.endswith(".wav")
    assert await storage.read(location) == b"audio"

    await storage.delete(location)
    with pytest.raises(FileNotFoundError):
        await storage.read(location)


@pytest.mark.asyncio
async def test_local_storage_reads_legacy_absolute_path(tmp_path: Path) -> None:
    storage = LocalStorageBackend(root=str(tmp_path))
    legacy_path = tmp_path / "legacy.wav"
    legacy_path.write_bytes(b"legacy audio")

    assert await storage.read(str(legacy_path.resolve())) == b"legacy audio"


@pytest.mark.asyncio
async def test_local_storage_accepts_legacy_container_path(tmp_path: Path) -> None:
    storage = LocalStorageBackend(root=str(tmp_path))

    with pytest.raises(FileNotFoundError):
        await storage.read("/app/storage/uploads/conversations/missing.wav")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "location",
    ["local://conversations/../../secret", "conversations/relative.wav"],
)
async def test_local_storage_rejects_unsafe_locations(tmp_path: Path, location: str) -> None:
    storage = LocalStorageBackend(root=str(tmp_path))

    with pytest.raises(InvalidStorageLocationError):
        await storage.read(location)


def test_storage_factory_builds_local_backend(tmp_path: Path) -> None:
    settings = Settings(storage_backend="local", storage_root=str(tmp_path))

    assert isinstance(build_storage_backend(settings), LocalStorageBackend)


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes) -> None:
        self.objects[(Bucket, Key)] = Body

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, BytesIO]:
        return {"Body": BytesIO(self.objects[(Bucket, Key)])}

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        self.objects.pop((Bucket, Key), None)


class FailingS3Client(FakeS3Client):
    def put_object(self, *, Bucket: str, Key: str, Body: bytes) -> None:
        raise RuntimeError("provider unavailable")


def _s3_storage(client: FakeS3Client) -> S3StorageBackend:
    return S3StorageBackend(
        endpoint_url="https://example.r2.cloudflarestorage.com",
        region="auto",
        bucket="conversation-os-staging",
        access_key_id="test-access-key",
        secret_access_key="test-secret-key",
        client=client,
    )


@pytest.mark.asyncio
async def test_s3_storage_contract_uses_private_location() -> None:
    client = FakeS3Client()
    storage = _s3_storage(client)

    location = await storage.save(filename="private-client-call.m4a", content=b"audio")

    assert location.startswith("s3://conversation-os-staging/conversations/")
    assert location.endswith(".m4a")
    assert "private-client-call" not in location
    assert await storage.read(location) == b"audio"

    await storage.delete(location)
    await storage.delete(location)
    with pytest.raises(KeyError):
        await storage.read(location)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "location",
    [
        "s3://another-bucket/conversations/file.wav",
        "s3://conversation-os-staging/other/file.wav",
        "s3://conversation-os-staging/conversations/../../secret",
    ],
)
async def test_s3_storage_rejects_invalid_locations(location: str) -> None:
    storage = _s3_storage(FakeS3Client())

    with pytest.raises(InvalidStorageLocationError):
        await storage.read(location)


@pytest.mark.asyncio
async def test_s3_storage_surfaces_provider_failure() -> None:
    storage = _s3_storage(FailingS3Client())

    with pytest.raises(RuntimeError, match="provider unavailable"):
        await storage.save(filename="recording.wav", content=b"audio")


def test_s3_configuration_fails_closed_when_incomplete() -> None:
    with pytest.raises(ValueError, match="S3_BUCKET"):
        Settings(storage_backend="s3")


def test_storage_factory_builds_s3_backend() -> None:
    settings = Settings(
        storage_backend="s3",
        s3_endpoint_url="https://example.r2.cloudflarestorage.com",
        s3_region="auto",
        s3_bucket="conversation-os-staging",
        s3_access_key_id="test-access-key",
        s3_secret_access_key="test-secret-key",
    )

    assert isinstance(build_storage_backend(settings), RoutingStorageBackend)


@pytest.mark.asyncio
async def test_routing_storage_preserves_local_locations(tmp_path: Path) -> None:
    local = LocalStorageBackend(root=str(tmp_path))
    s3 = _s3_storage(FakeS3Client())
    storage = RoutingStorageBackend(primary=s3, local=local, s3=s3)
    legacy_location = await local.save(filename="legacy.wav", content=b"legacy")

    new_location = await storage.save(filename="new.wav", content=b"new")

    assert new_location.startswith("s3://")
    assert await storage.read(new_location) == b"new"
    assert await storage.read(legacy_location) == b"legacy"
