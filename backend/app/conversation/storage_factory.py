"""Construct the configured storage backend for every runtime entry point."""

from app.conversation.storage import (
    LocalStorageBackend,
    RoutingStorageBackend,
    S3StorageBackend,
    StorageBackend,
)
from app.core.config import Settings


def build_storage_backend(settings: Settings) -> StorageBackend:
    if settings.storage_backend == "local":
        return LocalStorageBackend(root=settings.storage_root)
    local = LocalStorageBackend(root=settings.storage_root)
    s3 = S3StorageBackend(
        endpoint_url=settings.s3_endpoint_url or "",
        region=settings.s3_region or "",
        bucket=settings.s3_bucket or "",
        access_key_id=settings.s3_access_key_id or "",
        secret_access_key=settings.s3_secret_access_key or "",
    )
    return RoutingStorageBackend(primary=s3, local=local, s3=s3)
