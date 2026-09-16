"""Independent encrypted recording snapshots; never modifies source objects."""

import hashlib
import json
from pathlib import Path


def inventory(client, bucket):
    items = {}
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        for item in page.get("Contents", []):
            items[item["Key"]] = (item["ETag"], item["Size"])
    return items


def snapshot(
    source,
    source_bucket,
    target,
    target_bucket,
    prefix,
    key,
    directory,
    encrypt_file,
    verify_remote,
    file_hash,
    max_bytes,
):
    if source_bucket == target_bucket:
        raise ValueError("Recording source and backup buckets must differ")
    before = inventory(source, source_bucket)
    if sum(size for _, size in before.values()) > max_bytes:
        raise ValueError("Recording snapshot exceeds proof-of-concept size limit")
    objects = []
    for source_key, (etag, expected_size) in sorted(before.items()):
        # Opaque local filename avoids interpreting user-controlled storage keys as paths.
        plain = Path(directory) / "recording.tmp"
        encrypted = Path(directory) / "recording.enc"
        body = source.get_object(Bucket=source_bucket, Key=source_key, IfMatch=etag)[
            "Body"
        ]
        digest, size = hashlib.sha256(), 0
        try:
            with plain.open("wb") as output:
                while chunk := body.read(1024 * 1024):
                    size += len(chunk)
                    if size > expected_size or size > max_bytes:
                        raise ValueError("Source recording size changed")
                    digest.update(chunk)
                    output.write(chunk)
        finally:
            body.close()
        if size != expected_size:
            raise ValueError("Source recording was truncated")
        encrypt_file(plain, encrypted, key)
        target_key = (
            prefix + "/" + hashlib.sha256(source_key.encode()).hexdigest() + ".aesgcm"
        )
        target.upload_file(str(encrypted), target_bucket, target_key)
        cipher_hash = file_hash(encrypted)
        verify_remote(
            target, target_bucket, target_key, cipher_hash, encrypted.stat().st_size
        )
        objects.append(
            {
                "source_key": source_key,
                "source_etag": etag,
                "plaintext_bytes": size,
                "plaintext_sha256": digest.hexdigest(),
                "backup_key": target_key,
                "encrypted_sha256": cipher_hash,
                "encrypted_bytes": encrypted.stat().st_size,
            }
        )
        plain.unlink()
        encrypted.unlink()
    if inventory(source, source_bucket) != before:
        raise ValueError("Recording inventory changed during snapshot; retry required")
    manifest = {
        "format": "COSRECORDINGS1",
        "source_bucket": source_bucket,
        "objects": objects,
        "verified_download": True,
        "database_atomic_snapshot": False,
    }
    # Manifest is written last. Previous snapshots remain untouched on failure/deletion.
    target.put_object(
        Bucket=target_bucket,
        Key=prefix + ".json",
        Body=json.dumps(manifest).encode(),
        ContentType="application/json",
    )
    return len(objects)
