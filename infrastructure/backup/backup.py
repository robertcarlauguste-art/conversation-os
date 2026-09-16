"""One-shot encrypted PostgreSQL backup. No application imports or restore command."""

import base64
import hashlib
import json
import os
import subprocess
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import boto3
import httpx
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b"COSBACKUP1"
CHUNK = 1024 * 1024
MAX_BYTES = 256 * CHUNK


def encrypt_file(source, destination, key):
    nonce = os.urandom(12)
    header = MAGIC + nonce
    encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    encryptor.authenticate_additional_data(header)
    total = 0
    with source.open("rb") as src, destination.open("wb") as dst:
        dst.write(header)
        while chunk := src.read(CHUNK):
            total += len(chunk)
            if total > MAX_BYTES:
                raise ValueError("Backup exceeds proof-of-concept size limit")
            dst.write(encryptor.update(chunk))
        dst.write(encryptor.finalize())
        dst.write(encryptor.tag)
    return total


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def verify_remote(client, bucket, object_key, expected_hash, expected_size):
    response = client.get_object(Bucket=bucket, Key=object_key)
    body = response["Body"]
    digest = hashlib.sha256()
    size = 0
    try:
        while chunk := body.read(CHUNK):
            size += len(chunk)
            if size > expected_size:
                raise ValueError("Remote backup is larger than expected")
            digest.update(chunk)
    finally:
        body.close()
    if size != expected_size or digest.hexdigest() != expected_hash:
        raise ValueError("Remote backup verification failed")


def config():
    names = (
        "BACKUP_DATABASE_URL",
        "BACKUP_ENDPOINT_URL",
        "BACKUP_BUCKET",
        "BACKUP_ACCESS_KEY_ID",
        "BACKUP_SECRET_ACCESS_KEY",
        "BACKUP_ENCRYPTION_KEY",
        "BACKUP_HEARTBEAT_URL",
        "BACKUP_KEY_ID",
    )
    values = {name: os.environ[name].strip() for name in names}
    if not all(values.values()):
        raise ValueError("Backup configuration is incomplete")
    key = base64.b64decode(values["BACKUP_ENCRYPTION_KEY"], validate=True)
    if len(key) != 32:
        raise ValueError("Backup key must decode to 32 bytes")
    for name in ("BACKUP_ENDPOINT_URL", "BACKUP_HEARTBEAT_URL"):
        url = urlsplit(values[name])
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            raise ValueError(
                "Backup endpoints must use HTTPS without embedded credentials"
            )
    if values["BACKUP_BUCKET"] == os.environ.get(
        "S3_BUCKET", "conversation-os-staging"
    ):
        raise ValueError("Backup bucket must be separate from application recordings")
    return values, key


def connection_environment(url):
    normalized = url.replace("postgresql+asyncpg://", "postgresql://", 1).replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    parsed = urlsplit(normalized)
    if parsed.scheme not in ("postgresql", "postgres") or not parsed.hostname:
        raise ValueError("Expected a PostgreSQL connection URL")
    env = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
    env.update(
        PGHOST=parsed.hostname,
        PGPORT=str(parsed.port or 5432),
        PGUSER=unquote(parsed.username or "postgres"),
        PGPASSWORD=unquote(parsed.password or ""),
        PGDATABASE=unquote(parsed.path.lstrip("/")),
    )
    for name, values in parse_qs(parsed.query).items():
        if name not in ("sslmode", "channel_binding") or len(values) != 1:
            raise ValueError("Unsupported PostgreSQL URL option")
        env["PG" + name.upper().replace("_", "")] = values[0]
    env["PGCONNECT_TIMEOUT"] = "15"
    env["PGOPTIONS"] = "-c default_transaction_read_only=on -c statement_timeout=180000"
    return env


def dump_database(url, destination):
    # libpq does not expand a URI supplied through PGDATABASE. Pass fields separately.
    # Child process sees the database secret, never a command-line argument or log.
    env = connection_environment(url)

    # Linux container limit bounds disk consumption even if pg_dump grows unexpectedly.
    def limits():
        import resource

        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_BYTES, MAX_BYTES))

    result = subprocess.run(
        [
            "pg_dump",
            "--format=custom",
            "--no-owner",
            "--no-acl",
            "--lock-wait-timeout=15000",
            "--file",
            str(destination),
        ],
        env=env,
        check=False,
        capture_output=True,
        timeout=240,
        preexec_fn=limits,
    )
    if result.returncode or not destination.exists() or not destination.stat().st_size:
        error = result.stderr.decode(errors="replace").lower()
        categories = {
            "permission denied": "database_permission",
            "password authentication failed": "database_authentication",
            "could not translate host name": "database_dns",
            "connection refused": "database_connection",
            "server version": "database_version",
            "no password supplied": "database_password_missing",
            "read-only transaction": "database_read_only",
        }
        category = next(
            (v for k, v in categories.items() if k in error), "database_export"
        )
        print(
            json.dumps(
                {"backup_error_category": category, "exit_code": result.returncode}
            )
        )
        raise RuntimeError("Database export failed")


def run():
    print('{"backup_stage":"configuration"}', flush=True)
    values, key = config()
    client = boto3.client(
        "s3",
        endpoint_url=values["BACKUP_ENDPOINT_URL"],
        region_name="auto",
        aws_access_key_id=values["BACKUP_ACCESS_KEY_ID"],
        aws_secret_access_key=values["BACKUP_SECRET_ACCESS_KEY"],
    )
    created = datetime.now(UTC)
    prefix = "postgres/" + created.strftime("%Y/%m/%d/%H%M%S-") + uuid.uuid4().hex
    bucket = values["BACKUP_BUCKET"]
    with tempfile.TemporaryDirectory(prefix="cos-backup-") as directory:
        plain, encrypted = Path(directory) / "db.dump", Path(directory) / "db.enc"
        print('{"backup_stage":"database_export"}', flush=True)
        dump_database(values["BACKUP_DATABASE_URL"], plain)
        print('{"backup_stage":"encryption"}', flush=True)
        size = encrypt_file(plain, encrypted, key)
        digest = file_hash(encrypted)
        object_key = prefix + ".dump.aesgcm"
        print('{"backup_stage":"upload"}', flush=True)
        client.upload_file(str(encrypted), bucket, object_key)
        print('{"backup_stage":"download_verification"}', flush=True)
        verify_remote(client, bucket, object_key, digest, encrypted.stat().st_size)
        manifest = {
            "format": "COSBACKUP1",
            "created_at": created.isoformat(),
            "object_key": object_key,
            "sha256": digest,
            "plaintext_bytes": size,
            "encrypted_bytes": encrypted.stat().st_size,
            "key_id": values["BACKUP_KEY_ID"],
            "verified_download": True,
            "scope": "single PostgreSQL database; no audio, roles, or Redis",
        }
        client.put_object(
            Bucket=bucket,
            Key=prefix + ".json",
            Body=json.dumps(manifest).encode(),
            ContentType="application/json",
        )
    # Only verified uploads emit success. Missed/failed runs leave heartbeat overdue.
    response = httpx.get(
        values["BACKUP_HEARTBEAT_URL"], timeout=15, follow_redirects=False
    )
    response.raise_for_status()
    print(json.dumps({"backup": "verified", "created_at": created.isoformat()}))


if __name__ == "__main__":
    try:
        run()
    except Exception as error:  # noqa: BLE001
        print(json.dumps({"backup_exception_type": type(error).__name__}))
        # Provider errors may include credentials, URLs, or database content.
        print(
            '{"backup":"failed","detail":"Check configuration and provider availability"}'
        )
        raise SystemExit(1) from None
