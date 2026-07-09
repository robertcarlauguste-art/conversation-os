"""
Storage abstraction for uploaded audio files.

Same shape as `app/providers/ai_provider.py`: business logic depends
on `StorageBackend`, never on `open()`/filesystem calls directly, so
swapping to Supabase Storage or S3 later means adding one new class,
not touching `service.py`.

This lives inside the conversation slice for now since it's the only
consumer. If a second slice needs file storage, this should move to
a shared location (e.g. `app/shared/storage.py`) rather than being
duplicated — noted as a Sprint 2+ consideration in the ADR.
"""

import uuid
from abc import ABC, abstractmethod
from pathlib import Path

import aiofiles


class StorageBackend(ABC):
    """Abstract storage interface. One concrete class per backend."""

    @abstractmethod
    async def save(self, *, filename: str, content: bytes) -> str:
        """Persist `content` and return a backend-specific storage path/key."""
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
        self._root = Path(root) / "conversations"
        self._root.mkdir(parents=True, exist_ok=True)

    async def save(self, *, filename: str, content: bytes) -> str:
        extension = Path(filename).suffix
        stored_name = f"{uuid.uuid4()}{extension}"
        destination = self._root / stored_name
        async with aiofiles.open(destination, "wb") as f:
            await f.write(content)
        return str(destination)

    async def delete(self, storage_path: str) -> None:
        path = Path(storage_path)
        if path.exists():
            path.unlink()
