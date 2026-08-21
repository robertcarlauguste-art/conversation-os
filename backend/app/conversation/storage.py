"""
Storage abstraction for uploaded audio files.

Same shape as `app/providers/ai_provider.py`: business logic depends
on `StorageBackend`, never on `open()`/filesystem calls directly, so
swapping to Supabase Storage or S3 later means adding one new class,
not touching `service.py`.

This lives inside the conversation slice for now since it's the only
owner. The transcription slice imports this module directly to read
stored audio (see transcription/service.py) — cross-slice import,
tracked as TD-001 rather than resolved this sprint. That docstring
note above turned out to be exactly right: a second slice needing
storage is precisely the trigger condition it named.
"""

import uuid
from abc import ABC, abstractmethod
from asyncio import to_thread
from pathlib import Path
from typing import Any

import aiofiles

LOCAL_STORAGE_PREFIX = "local://"
S3_STORAGE_PREFIX = "s3://"


class InvalidStorageLocationError(ValueError):
    """Raised when a storage location is malformed or escapes its backend root."""


class StorageBackend(ABC):
    """Abstract storage interface. One concrete class per backend."""

    @abstractmethod
    async def save(self, *, filename: str, content: bytes) -> str:
        """Persist `content` and return a backend-specific storage path/key."""
        raise NotImplementedError

    @abstractmethod
    async def read(self, storage_path: str) -> bytes:
        """Read back previously stored content."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, storage_path: str) -> None:
        """Remove a previously stored file. Safe to call on a missing file."""
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    """
    Development implementation: writes to a local directory.

    Sprint 1 scope per spec — Supabase Storage / S3 backends are a
    future sprint's concern and will subclass StorageBackend the same
    way OpenAIProvider will subclass AIProvider.
    """

    def __init__(self, root: str) -> None:
        self._base_root = Path(root).resolve()
        self._root = self._base_root / "conversations"
        self._root.mkdir(parents=True, exist_ok=True)

    async def save(self, *, filename: str, content: bytes) -> str:
        extension = Path(filename).suffix
        stored_name = f"{uuid.uuid4()}{extension}"
        destination = self._root / stored_name
        async with aiofiles.open(destination, "wb") as f:
            await f.write(content)
        return f"{LOCAL_STORAGE_PREFIX}conversations/{stored_name}"

    async def read(self, storage_path: str) -> bytes:
        path = self._resolve(storage_path)
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete(self, storage_path: str) -> None:
        path = self._resolve(storage_path)
        if path.exists():
            path.unlink()

    def _resolve(self, storage_path: str) -> Path:
        if storage_path.startswith(LOCAL_STORAGE_PREFIX):
            relative_path = storage_path.removeprefix(LOCAL_STORAGE_PREFIX)
            candidate = (self._base_root / relative_path).resolve()
            if not candidate.is_relative_to(self._root):
                raise InvalidStorageLocationError(
                    "Local storage location must remain inside the conversations directory"
                )
            return candidate

        # Records created before Sprint 6 contain absolute filesystem paths.
        legacy_path = Path(storage_path)
        if not (legacy_path.is_absolute() or storage_path.startswith("/")):
            raise InvalidStorageLocationError(
                "Legacy local storage locations must be absolute paths"
            )
        return legacy_path


class S3StorageBackend(StorageBackend):
    """Private S3-compatible object storage implementation."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        region: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        client: Any | None = None,
    ) -> None:
        self._bucket = bucket
        if client is None:
            import boto3

            client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                region_name=region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
            )
        self._client = client

    async def save(self, *, filename: str, content: bytes) -> str:
        extension = Path(filename).suffix
        object_key = f"conversations/{uuid.uuid4()}{extension}"
        await to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=object_key,
            Body=content,
        )
        return f"{S3_STORAGE_PREFIX}{self._bucket}/{object_key}"

    async def read(self, storage_path: str) -> bytes:
        object_key = self._object_key(storage_path)
        response = await to_thread(
            self._client.get_object,
            Bucket=self._bucket,
            Key=object_key,
        )
        return await to_thread(response["Body"].read)

    async def delete(self, storage_path: str) -> None:
        object_key = self._object_key(storage_path)
        await to_thread(
            self._client.delete_object,
            Bucket=self._bucket,
            Key=object_key,
        )

    def _object_key(self, storage_path: str) -> str:
        expected_prefix = f"{S3_STORAGE_PREFIX}{self._bucket}/conversations/"
        if not storage_path.startswith(expected_prefix):
            raise InvalidStorageLocationError(
                "S3 storage location must reference the configured bucket and conversations prefix"
            )
        object_key = storage_path.removeprefix(f"{S3_STORAGE_PREFIX}{self._bucket}/")
        if not object_key or "/../" in f"/{object_key}/" or object_key.endswith("/.."):
            raise InvalidStorageLocationError("S3 storage location contains an unsafe object key")
        return object_key


class RoutingStorageBackend(StorageBackend):
    """Save to the primary backend and route existing locations by scheme."""

    def __init__(
        self,
        *,
        primary: StorageBackend,
        local: LocalStorageBackend,
        s3: S3StorageBackend,
    ) -> None:
        self._primary = primary
        self._local = local
        self._s3 = s3

    async def save(self, *, filename: str, content: bytes) -> str:
        return await self._primary.save(filename=filename, content=content)

    async def read(self, storage_path: str) -> bytes:
        return await self._backend_for(storage_path).read(storage_path)

    async def delete(self, storage_path: str) -> None:
        await self._backend_for(storage_path).delete(storage_path)

    def _backend_for(self, storage_path: str) -> StorageBackend:
        if storage_path.startswith(S3_STORAGE_PREFIX):
            return self._s3
        return self._local
